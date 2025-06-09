// components/GradientIconButton.js

import React from 'react';
import { TouchableOpacity, View, StyleSheet, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';

interface GradientIconButtonProps {
  name: keyof typeof Ionicons.glyphMap;
  size?: number;
  color?: string;
  colors?: readonly [string, string, ...string[]];
  radius?: number;
  onPress?: () => void;
  style?: ViewStyle;
}

export default function GradientIconButton({
  name,
  size = 24,
  color = '#000000',
  colors = ['#ffffff', '#f2f2f2', '#b3b3b3'],
  radius = size * 0.4, // default to roughly circle
  onPress,
  style,
}: GradientIconButtonProps) {
  const dimension = size * 1.8;

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.7}>
      <View style={styles.shadow}>
        <LinearGradient
          colors={colors}
          start={[0, 0]}
          end={[1, 1]}
          style={[
            styles.gradient,
            { width: dimension, height: dimension, borderRadius: radius },
            style,
          ]}>
          <Ionicons name={name} size={size} color={color} />
        </LinearGradient>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  gradient: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  shadow: {
    borderRadius:8,
    shadowColor: '#000',
    shadowOffset: { width: 2, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
  },
});
