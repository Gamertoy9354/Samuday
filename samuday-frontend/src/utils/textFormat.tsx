import React from 'react';

/**
 * Lightweight markdown-ish renderer shared by the AI Shopping Copilot, the AI
 * Seller Advisor chat, and product descriptions. Supports the subset of markdown
 * that Samuday's AI text generators (NVIDIA LLM prompts) actually produce:
 * headings (###), bold (**text**), bullet lists (- / *), numbered lists (1.),
 * and pipe tables (| a | b |). Anything else renders as plain text.
 */
function renderInline(text: string, keyPrefix: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  const boldRegex = /\*\*(.*?)\*\*/g;
  let match;
  let lastIndex = 0;
  let i = 0;

  while ((match = boldRegex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.substring(lastIndex, match.index));
    parts.push(<strong key={`${keyPrefix}-b${i++}`}>{match[1]}</strong>);
    lastIndex = boldRegex.lastIndex;
  }
  if (lastIndex < text.length) parts.push(text.substring(lastIndex));
  return parts.length > 0 ? parts : text;
}

function isTableSeparatorRow(line: string): boolean {
  return /^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?$/.test(line.trim());
}

function parseTableRow(line: string): string[] {
  return line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
}

export function renderFormattedText(text: string): React.ReactNode {
  if (!text) return null;
  const lines = text.split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Markdown table: a header row, a separator row, then 1+ data rows
    if (trimmed.startsWith('|') && lines[i + 1] && isTableSeparatorRow(lines[i + 1])) {
      const headerCells = parseTableRow(trimmed);
      const rows: string[][] = [];
      let j = i + 2;
      while (j < lines.length && lines[j].trim().startsWith('|')) {
        rows.push(parseTableRow(lines[j]));
        j++;
      }
      blocks.push(
        <div key={`tbl-${i}`} style={{ overflowX: 'auto', margin: '8px 0' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.84rem' }}>
            <thead>
              <tr>
                {headerCells.map((c, ci) => (
                  <th key={ci} style={{ textAlign: 'left', padding: '6px 10px', borderBottom: '2px solid var(--border-card, #e2e8f0)', fontWeight: 700 }}>
                    {renderInline(c, `th-${i}-${ci}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri}>
                  {r.map((c, ci) => (
                    <td key={ci} style={{ padding: '6px 10px', borderBottom: '1px solid var(--border-light, #eef0f4)' }}>
                      {renderInline(c, `td-${i}-${ri}-${ci}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      i = j;
      continue;
    }

    // Heading (### text)
    const headingMatch = trimmed.match(/^(#{1,4})\s+(.*)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const size = level === 1 ? '1.15rem' : level === 2 ? '1.05rem' : '0.95rem';
      blocks.push(
        <div key={i} style={{ fontWeight: 700, fontSize: size, margin: '10px 0 4px' }}>
          {renderInline(headingMatch[2], `h-${i}`)}
        </div>
      );
      i++;
      continue;
    }

    // Bullet list item
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const content = trimmed.replace(/^[-*]\s+/, '');
      blocks.push(
        <div key={i} style={{ display: 'flex', gap: 6, margin: '4px 0 4px 8px', fontSize: '0.86rem', lineHeight: 1.45 }}>
          <span>•</span>
          <span>{renderInline(content, `li-${i}`)}</span>
        </div>
      );
      i++;
      continue;
    }

    // Numbered list item
    const numberedMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (numberedMatch) {
      blocks.push(
        <div key={i} style={{ display: 'flex', gap: 6, margin: '4px 0 4px 8px', fontSize: '0.86rem', lineHeight: 1.45 }}>
          <span>{numberedMatch[1]}.</span>
          <span>{renderInline(numberedMatch[2], `ol-${i}`)}</span>
        </div>
      );
      i++;
      continue;
    }

    if (trimmed.length === 0) {
      i++;
      continue;
    }

    blocks.push(
      <p key={i} style={{ margin: '4px 0', fontSize: '0.86rem', lineHeight: 1.5 }}>
        {renderInline(line, `p-${i}`)}
      </p>
    );
    i++;
  }

  return blocks;
}
