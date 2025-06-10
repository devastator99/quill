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
    alignItems: 'center',
    width: '90%',
  },
  shadowContainer: {
    // match container size and borderRadius
    width: '90%',
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.8,
    shadowRadius: 8,

    // dark, vibrant shadow
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.9,
        shadowRadius: 10,
      },
      android: {
        elevation: 15,
      },
    }),
  },
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E5EA',
  },
  input: {
    flex: 1,
    fontFamily: 'Urbanist_500Medium',
    fontSize: 14,
    paddingVertical: 0,
    margin: 0,
    color: '#000',
  },
  iconTouch: {
    marginLeft: 12,
  },
});
