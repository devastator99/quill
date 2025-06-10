import React from 'react';
import { TouchableOpacity, Text, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import FontAwesome5 from '@expo/vector-icons/FontAwesome5';

export default function RegenerateButton({ onPress, style }: { onPress: () => void, style: any }) {
  return (
    <TouchableOpacity onPress={onPress} style={style}>
      <View style={styles.btn}>
        <FontAwesome5 name="retweet" size={10} style={styles.icon}/>
        <Text style={styles.text}>Regenerate Response</Text>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  btn: {
    width: 120, // fixed width
    height:30,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 6,
    borderWidth: 0,
    borderColor: '#909090',
    borderRadius: 4,
    // no backgroundColor → transparent
  },
  icon: {
    marginRight: 6,
    color: '#909090',
  },
  text: {
    color: '#909090',
    fontSize: 10,
    fontFamily: 'Urbanist_500Medium',
  },
});
