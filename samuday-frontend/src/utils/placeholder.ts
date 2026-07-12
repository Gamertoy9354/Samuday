// Inline SVG data URI — via.placeholder.com is no longer reachable, so it can't
// be used as an image fallback (it would just replace one broken image with another).
export const FALLBACK_IMAGE = 'data:image/svg+xml;utf8,' + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
    <rect width="300" height="300" fill="#f0f0f0"/>
    <text x="50%" y="50%" font-family="sans-serif" font-size="16" fill="#999" text-anchor="middle" dominant-baseline="middle">No Image</text>
  </svg>`
);
