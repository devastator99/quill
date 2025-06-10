import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import GradientIconButton from './IconComponent';

export default function Header({ title, onBack, onMenu }: { title: string, onBack: () => void, onMenu: () => void }) {
  return (
    <View style={styles.header}>
      <TouchableOpacity onPress={onBack}>
        <GradientIconButton
          name="arrow-back"
          size={20}
          style={{ margin: 8 }}
          onPress={() => {
            console.log('Back pressed');
          }}
        />
      </TouchableOpacity>
      <Text style={styles.title}>{title}</Text>
      <TouchableOpacity onPress={onMenu}>
        <Ionicons name="ellipsis-vertical" size={16} style={{ margin: 11 }} color="black" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    // borderBottomWidth: 1,
    // borderColor: '#E5E5EA',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    fontFamily: 'Urbanist_600SemiBold',
  },
});
