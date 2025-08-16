module.exports = function (api) {
  api.cache(true);
  return {
    presets: ["babel-preset-expo"],
    plugins: [
      "react-native-reanimated/plugin",
      [
        "module-resolver",
        ["babel-plugin-transform-import-meta", { replace: { module: {} } }],

        {
          alias: {
            // Steer these packages to their CJS files
            multiformats: "multiformats/cjs/src/index.js",
            "rpc-websockets": "rpc-websockets/dist/index.cjs",
            // Force noble to a file that doesn't rely on import.meta
            "@noble/hashes/crypto.js": "@noble/hashes/lib/crypto.js",
          },
        },
      ],
    ],
  };
};
