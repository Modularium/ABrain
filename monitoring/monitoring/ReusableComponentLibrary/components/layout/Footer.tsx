// Footer.tsx - Footer component for the dashboard
import React from 'react';

const Footer: React.FC = () => {
  return (
    <footer className="bg-white dark:bg-gray-800 shadow-md py-3 px-6 text-center border-t border-gray-200 dark:border-gray-700">
      <div className="text-sm text-gray-500 dark:text-gray-400">
        <p>© 2025 ABrain Dashboard. All rights reserved.</p>
        <p className="mt-1 text-xs">
          Version 2.0.0 | <a href="#" className="text-indigo-600 dark:text-indigo-400 hover:underline">View Changelog</a> | <a href="#" className="text-indigo-600 dark:text-indigo-400 hover:underline">Report Issue</a>
        </p>
      </div>
    </footer>
  );
};

export default Footer;
