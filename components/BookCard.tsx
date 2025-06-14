// components/BookCard.tsx

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  ImageSourcePropType,
} from 'react-native';
import ImageColors from 'react-native-image-colors';
import { Star } from 'lucide-react-native';

export interface BookCardProps {
  id: string;
  coverUri: string;
  title: string;
  author: string;
  rating: number;
  year: number;
  onPress: (id: string) => void;
}

export default function BookCard({
  id,
  coverUri,
  title,
  author,
  rating,
  year,
  onPress,
}: BookCardProps) {
  const [borderColor, setBorderColor] = useState('#ccc');

  useEffect(() => {
    let isMounted = true;
    ImageColors.getColors(coverUri, { fallback: '#ccc' }).then((colors) => {
      if (!isMounted) return;
      // Android and iOS return different keys
      const color =
        colors.platform === 'android'
          ? colors.dominant || colors.average
          : colors.platform === 'ios'
          ? colors.background
          : colors.dominant;
      if (color) setBorderColor(color);
    });
    return () => {
      isMounted = false;
    };
  }, [coverUri]);

  return (
    <TouchableOpacity
      style={[styles.card, {
        borderColor,
        shadowColor: borderColor,
      }]}
      activeOpacity={0.8}
      onPress={() => onPress(id)}
    >
      <Image source={{ uri: coverUri }} style={styles.cover} />

      <View style={styles.info}>
        <Text style={styles.title} numberOfLines={2}>
          {title}
        </Text>
        <Text style={styles.author} numberOfLines={1}>
          {author}
        </Text>

        <View style={styles.metaRow}>
          <Star size={14} color="#fbbf24" fill="#fbbf24" />
          <Text style={styles.rating}>{rating.toFixed(1)}</Text>
          <Text style={styles.year}>{year}</Text>
        </View>
      </View>
    </TouchableOpacity>
  );
}

const CARD_WIDTH = 160;
const COVER_HEIGHT = 240;

const styles = StyleSheet.create({
  card: {
    width: CARD_WIDTH,
    borderRadius: 12,
    borderWidth: 2,
    overflow: 'hidden',
    backgroundColor: '#fff',
    // iOS shadow
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    // Android shadow
    elevation: 5,
    margin: 8,
  },
  cover: {
    width: '100%',
    height: COVER_HEIGHT,
    resizeMode: 'cover',
    backgroundColor: '#e5e7eb',
  },
  info: {
    padding: 8,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: 4,
  },
  author: {
    fontSize: 12,
    fontStyle: 'italic',
    color: '#6b7280',
    marginBottom: 8,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  rating: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1f2937',
    marginLeft: 4,
    marginRight: 8,
  },
  year: {
    fontSize: 12,
    color: '#9ca3af',
  },
});
