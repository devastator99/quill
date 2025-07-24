import { TouchableOpacity, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '@/styles/theme';

interface SuggestedPromptProps {
  prompt: string;
  onPress: (prompt: string) => void;
}

export default function SuggestedPrompt({ prompt, onPress }: SuggestedPromptProps) {
  return (
    <TouchableOpacity 
      style={styles.container} 
      onPress={() => onPress(prompt)}

    >
      <Text style={styles.text}>{prompt}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 12,
    marginVertical: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
  },
  text: {
    ...typography.body,
    color: colors.text,
    textAlign: 'center',
  },
});