// babel.config.js
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    plugins: [
      ['module-resolver', {
        // root: ['.'], // optional, add if you need absolute imports from project root
        alias: {
          // Steer these packages to their CJS files
          multiformats: './node_modules/multiformats/cjs',
          'rpc-websockets': './node_modules/rpc-websockets/dist/index.cjs',
          // Force noble to a file that doesn't rely on import.meta
          '@noble/hashes/crypto.js': '@noble/hashes/lib/crypto.js',
        },
        extensions: ['.ts', '.tsx', '.js', '.json'],
      }],

      ['babel-plugin-transform-import-meta', { module: 'CommonJS' }],

      'react-native-reanimated/plugin',
    ],
  };
};
