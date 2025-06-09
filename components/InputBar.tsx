// components/InputBar.js

import React from 'react';
import {
  View,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Platform,
  ViewStyle,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

export default function InputBar({ 
  value, 
  onChangeText, 
  onSend, 
  onMic, 
  style 
}: { 
  value: string;
  onChangeText: (text: string) => void;
  onSend: () => void;
  onMic: () => void;
  style?: ViewStyle;
}) {
  const insets = useSafeAreaInsets();
  const isActive = value.trim().length > 0;

  const handlePress = () => {
    if (isActive) {
      onSend();
    } else if (onMic) {
      onMic();
    }
  };

  return (
    <View
      style={[
        styles.wrapper,
        { bottom: insets.bottom + 20 }, // float above safe area
        style,
      ]}>
      {/* Shadow wrapper */}
      <View style={styles.shadowContainer}>
        {/* Actual input container */}
        <View style={styles.container}>
          <TextInput
            style={styles.input}
            value={value}
            onChangeText={onChangeText}
            placeholder="Type a message"
            placeholderTextColor="#999"
            returnKeyType="send"
            onSubmitEditing={() => isActive && onSend()}
          />
          <TouchableOpacity onPress={handlePress} style={styles.iconTouch}>
            <Ionicons
              name={isActive ? 'send' : 'mic'}
              size={20}
              color={isActive ? '#007AFF' : '#AAA'}
            />
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    position: 'absolute',
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  shadowContainer: {
    // match container size and borderRadius
    width: '70%',
    maxWidth: 600,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 2, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 5,

    // dark, thin shadow
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 1, height: 1 },
        shadowOpacity: 0.6,
        shadowRadius: 2,
      },
      android: {
        elevation: 9,
      },
    }),
  },
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E5EA',
  },
  input: {
    flex: 1,
    fontFamily: 'Urbanist_500Medium',
    fontSize: 13,
    paddingVertical: 0,
    margin: 0,
    color: '#000',
  },
  iconTouch: {
    marginLeft: 12,
  },
});
