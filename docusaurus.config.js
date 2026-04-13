// @ts-check
/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'ABrain Documentation',
  url: 'https://ecospheretwork.github.io',
  baseUrl: '/ABrain/',
  organizationName: 'EcoSphereNetwork',
  projectName: 'ABrain',
  deploymentBranch: 'gh-pages',
  trailingSlash: false,
  favicon: 'img/favicon.ico',
  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */ ({
        docs: {
          path: 'docs',
          routeBasePath: '/',
          sidebarPath: require.resolve('./sidebars.js'),
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],
};
module.exports = config;
