import React from 'react';

export const Footer: React.FC = () => (
  <footer className="footer">
    <div className="footer-inner">
      <div className="footer-col">
        <h4>About</h4>
        <a href="#">About Samuday</a>
        <a href="#">Contact Us</a>
        <a href="#">Careers</a>
        <a href="#">Press</a>
      </div>
      <div className="footer-col">
        <h4>Help</h4>
        <a href="#">Payments</a>
        <a href="#">Shipping</a>
        <a href="#">Cancellation & Returns</a>
        <a href="#">FAQ</a>
      </div>
      <div className="footer-col">
        <h4>Policy</h4>
        <a href="#">Return Policy</a>
        <a href="#">Terms of Use</a>
        <a href="#">Privacy</a>
        <a href="#">Security</a>
      </div>
      <div className="footer-col">
        <h4>Social</h4>
        <a href="#">Facebook</a>
        <a href="#">Twitter</a>
        <a href="#">YouTube</a>
        <a href="#">Instagram</a>
      </div>
    </div>
    <div className="footer-bottom">
      &copy; {new Date().getFullYear()} Samuday Community Marketplace. All rights reserved. Built for India.
    </div>
  </footer>
);
