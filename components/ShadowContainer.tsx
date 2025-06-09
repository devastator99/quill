
import React from 'react';
import { View, Image, StyleSheet, Platform, ImageSourcePropType } from 'react-native';

export default function ShadowContainer({
  imageSource,
  containerStyle,
  imageStyle,
}: {
  imageSource: ImageSourcePropType,
  containerStyle: any,
  imageStyle: any,
}) {
  return (
    <View style={[styles.shadowContainer, containerStyle]}>
      <Image
        source={imageSource}
        style={[styles.image, imageStyle]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  shadowContainer: {
    // required on Android to see elevation
    backgroundColor: 'rgba(0,0,0,0)',

    // Android elevation
    elevation: 6,

    // iOS shadow
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 4,

    // ensure iOS shadow isn’t clipped
    overflow: Platform.OS === 'ios' ? 'visible' : 'hidden',

    // default rounding
    borderRadius: 8,
  },
  image: {
    // default size—override via imageStyle
    width: 30,
    height: 30,
    borderRadius: 8, // match container
  },
});
