module.exports = {
  preset: 'jest-expo',
  testRegex: '(/__tests__/.*|(\.|/)(test|spec))\\.(jsx?|tsx?)$',
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  transformIgnorePatterns: [
    "node_modules/(?!(react-native|@react-native|expo(-.*)?|expo-modules-core|react-native-reanimated|@expo|@unimodules|unimodules|@react-navigation|@react-native-community|@expo/vector-icons)/)"
  ],
  setupFiles: [
    './node_modules/react-native-gesture-handler/jestSetup.js'
  ],
}; 