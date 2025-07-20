const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');
const fs = require('fs');

const config = getDefaultConfig(__dirname);

// Add node modules path for better resolution
config.resolver.nodeModulesPaths = [
  path.resolve(__dirname, 'node_modules'),
];

// Add platform extensions for web
config.resolver.platforms = ['web', 'native', 'ios', 'android'];

// Configure resolver main fields
config.resolver.resolverMainFields = ['browser', 'main', 'react-native'];

// Custom resolver for Ledger package
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (moduleName.startsWith('@ledgerhq/devices/')) {
    const subpath = moduleName.replace('@ledgerhq/devices/', '');
    const resolvedPath = path.resolve(__dirname, `node_modules/@ledgerhq/devices/lib-es/${subpath}.js`);
    
    // Check if file exists before resolving
    if (fs.existsSync(resolvedPath)) {
      return {
        filePath: resolvedPath,
        type: 'sourceFile',
      };
    }
  }

  if (moduleName === '@reown/appkit/core') {
    const resolvedPath = path.resolve(__dirname, 'node_modules/@reown/appkit/dist/esm/exports/core.js');
    if (fs.existsSync(resolvedPath)) {
      return {
        filePath: resolvedPath,
        type: 'sourceFile',
      };
    }
  }

  if (moduleName === '@reown/appkit/networks') {
    const resolvedPath = path.resolve(__dirname, 'node_modules/@reown/appkit/dist/esm/exports/networks.js');
    if (fs.existsSync(resolvedPath)) {
      return {
        filePath: resolvedPath,
        type: 'sourceFile',
      };
    }
  }

  // Replace ws module with a web-compatible version for web builds
  if (moduleName === 'ws' && platform === 'web') {
    return {
      filePath: path.resolve(__dirname, 'polyfills/ws.js'),
      type: 'sourceFile',
    };
  }

  // Replace react-native-document-picker with a web-compatible version for web builds
  if (moduleName === 'react-native-document-picker' && platform === 'web') {
    return {
      filePath: path.resolve(__dirname, 'polyfills/document-picker.js'),
      type: 'sourceFile',
    };
  }

  // Handle @reown/appkit-scaffold-ui submodules
  if (moduleName.startsWith('@reown/appkit-scaffold-ui/')) {
    const submodule = moduleName.replace('@reown/appkit-scaffold-ui/', '');
    const resolvedPath = path.resolve(__dirname, `node_modules/@reown/appkit-scaffold-ui/dist/esm/exports/${submodule}.js`);
    if (fs.existsSync(resolvedPath)) {
      return {
        filePath: resolvedPath,
        type: 'sourceFile',
      };
    }
  }

  // Handle @reown/appkit-ui submodules
  if (moduleName.startsWith('@reown/appkit-ui/')) {
    const submodule = moduleName.replace('@reown/appkit-ui/', '');
    const resolvedPath = path.resolve(__dirname, `node_modules/@reown/appkit-ui/dist/esm/exports/${submodule}.js`);
    if (fs.existsSync(resolvedPath)) {
      return {
        filePath: resolvedPath,
        type: 'sourceFile',
      };
    }
  }

  // Handle @reown/appkit-ui main module
  if (moduleName === '@reown/appkit-ui') {
    const resolvedPath = path.resolve(__dirname, 'node_modules/@reown/appkit-ui/dist/esm/exports/index.js');
    if (fs.existsSync(resolvedPath)) {
      return {
        filePath: resolvedPath,
        type: 'sourceFile',
      };
    }
  }

  // Handle @reown/appkit-wallet submodules
  if (moduleName.startsWith('@reown/appkit-wallet/')) {
    const submodule = moduleName.replace('@reown/appkit-wallet/', '');
    const resolvedPath = path.resolve(__dirname, `node_modules/@reown/appkit-wallet/dist/esm/exports/${submodule}.js`);
    if (fs.existsSync(resolvedPath)) {
      return {
        filePath: resolvedPath,
        type: 'sourceFile',
      };
    }
  }

  // Handle @reown/appkit-utils submodules
  if (moduleName.startsWith('@reown/appkit-utils/')) {
    const submodule = moduleName.replace('@reown/appkit-utils/', '');
    const resolvedPath = path.resolve(__dirname, `node_modules/@reown/appkit-utils/dist/esm/exports/${submodule}.js`);
    if (fs.existsSync(resolvedPath)) {
      return {
        filePath: resolvedPath,
        type: 'sourceFile',
      };
    }
  }

  // Let Metro resolve other modules normally
  return context.resolveRequest(context, moduleName, platform);
};

// Configure asset extensions
config.resolver.assetExts = [
  ...config.resolver.assetExts,
  'bin',
  'txt',
  'jpg',
  'png',
  'json',
  'svg',
  'gif',
  'webp',
  'mp4',
  'webm',
  'wav',
  'mp3',
  'm4a',
  'aac',
  'oga',
  'ttf',
  'woff',
  'woff2',
  'eot',
  'otf',
];

// Add source extensions
config.resolver.sourceExts = [
  ...config.resolver.sourceExts,
  'jsx',
  'js',
  'ts',
  'tsx',
  'json',
  'wasm',
  'svg',
];

module.exports = config;
