const { heroui } = require("@heroui/react");

module.exports = {
  // ... existing Tailwind config
  plugins: [
    heroui({
      themes: {
        light: {
          colors: {
            primary: "#000000",      // Pure black
            secondary: "#222222",    // Dark gray
            background: "#FFFFFF",   // White
            text: "#000000",         // Black text
            border: "#222222",       // Dark gray border
          }
        },
        dark: {
          colors: {
            primary: "#FFFFFF",      // White for dark mode
            secondary: "#000000",    // Black for dark mode
            background: "#000000",   // Black background
            text: "#FFFFFF",         // White text
            border: "#FFFFFF",       // White border
          }
        },
      },
    }),
  ],
  // ... rest of your config
}; 