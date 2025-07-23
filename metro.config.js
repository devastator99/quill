const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const config = getDefaultConfig(__dirname);

// Ensure proper module resolution
config.resolver.platforms = ['ios', 'android', 'native', 'web'];

// Add resolver configuration
config.resolver.resolverMainFields = ['react-native', 'browser', 'main'];

// Add path alias configuration
config.resolver.extraNodeModules = {
  ...config.resolver.extraNodeModules,
  '@': path.resolve(__dirname, '.'),
};

// Add this section to ignore problematic source maps
config.transformer = {
  ...config.transformer,
  getTransformOptions: async () => ({
    transform: {
      experimentalImportSupport: false,
      inlineRequires: false,
    },
  }),
};

config.server = {
  ...config.server,
  enhanceMiddleware: (middleware) => {
    return (req, res, next) => {
      if (req.url.includes('<anonymous>') || req.url.includes('5112595-best-practices-for-api-key-safety')) {
        res.end();
        return;
      }
      return middleware(req, res, next);
    };
  }
};

module.exports = config;
