// Extract the Electron ASAR container used by the associated Tyrano work.
const path = require('path');
const asar = require('@electron/asar');
if (process.argv.length !== 4) {
  console.error('Usage: node scripts/agastar_unpack.cjs <app.asar> <output directory>');
  process.exit(2);
}
asar.extractAll(path.resolve(process.argv[2]), path.resolve(process.argv[3]));
