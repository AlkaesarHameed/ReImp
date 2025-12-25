import { nxE2EPreset } from '@nx/cypress/plugins/cypress-preset';
import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    ...nxE2EPreset(__filename, {
      cypressDir: 'apps/claims-portal-e2e',
      webServerCommands: {
        default: 'nx run claims-portal:serve:development',
        production: 'nx run claims-portal:serve:production',
      },
    }),
  },
});
