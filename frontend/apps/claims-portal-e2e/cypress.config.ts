import { nxE2EPreset } from '@nx/cypress/plugins/cypress-preset';
import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    ...nxE2EPreset(__filename, {
      cypressDir: 'src',
      bundler: 'vite',
      webServerCommands: {
        default: 'npx nx serve claims-portal',
        production: 'npx nx serve claims-portal --configuration=production',
      },
      ciWebServerCommand: 'npx nx serve claims-portal --configuration=production',
    }),
    baseUrl: 'http://localhost:4200',
    specPattern: 'src/**/*.cy.ts',
    supportFile: 'src/support/e2e.ts',
    fixturesFolder: 'src/fixtures',
    viewportWidth: 1280,
    viewportHeight: 720,
    video: false,
    screenshotOnRunFailure: true,
    retries: {
      runMode: 2,
      openMode: 0,
    },
  },
});
