import React from 'react';
import { View, Text, StyleSheet, Image } from 'react-native';
import { colors, typography, spacing } from '@/styles/theme';

interface ChatMessageProps {
  message: string;
  timestamp: string;
  isUser: boolean;
  avatar?: string;
}

export default function ChatMessage({ message, timestamp, isUser, avatar }: ChatMessageProps) {
  return (
    <View style={[styles.container, isUser ? styles.userContainer : styles.assistantContainer]}>
      {!isUser && (
        <Image 
          source={{ uri: avatar || 'https://images.pexels.com/photos/4792081/pexels-photo-4792081.jpeg?auto=compress&cs=tinysrgb&w=100&h=100&fit=crop' }} 
          style={styles.avatar} 
        />
      )}
      
      <View style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}>
        <Text style={[styles.message, isUser ? styles.userMessage : styles.assistantMessage]}>
          {message}
        </Text>
        <Text style={[styles.timestamp, isUser ? styles.userTimestamp : styles.assistantTimestamp]}>
          {timestamp}
        </Text>
      </View>
      
      {isUser && (
        <Image 
          source={{ uri: 'https://images.pexels.com/photos/1036622/pexels-photo-1036622.jpeg?auto=compress&cs=tinysrgb&w=100&h=100&fit=crop' }} 
          style={styles.avatar} 
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    marginVertical: spacing.xs,
    paddingHorizontal: spacing.md,
  },
  userContainer: {
    justifyContent: 'flex-end',
  },
  assistantContainer: {
    justifyContent: 'flex-start',
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    marginHorizontal: spacing.xs,
  },
  bubble: {
    maxWidth: '70%',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 16,
  },
  userBubble: {
    backgroundColor: colors.primary,
    borderBottomRightRadius: 4,
  },
  assistantBubble: {
    backgroundColor: colors.surface,
    borderBottomLeftRadius: 4,
  },
  message: {
    ...typography.body,
  },
  userMessage: {
    color: colors.textLight,
  },
  assistantMessage: {
    color: colors.text,
  },
  timestamp: {
    ...typography.caption,
    marginTop: spacing.xs,
  },
  userTimestamp: {
    color: colors.textLight,
    opacity: 0.8,
  },
  assistantTimestamp: {
    color: colors.textSecondary,
  },
});