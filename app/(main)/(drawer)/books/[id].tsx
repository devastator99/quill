import React from 'react';
import {
  View,
  Text,
  ScrollView,
  Image,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  StatusBar,
  Dimensions,
} from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import { ArrowLeft, Star, Calendar, BookOpen, Hash } from 'lucide-react-native';
import { booksData } from '@/data/books';

const { width } = Dimensions.get('window');

export default function BookDetailsScreen() {
  const { id } = useLocalSearchParams();
  const book = booksData.find(b => b.id === id);

  if (!book) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>Book not found</Text>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Text style={styles.backButtonText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#1f2937" />
      
      {/* Custom Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerButton}>
          <ArrowLeft size={24} color="#ffffff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>
          {book.title}
        </Text>
        <View style={styles.headerButton} />
      </View>

      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Book Cover */}
        <View style={styles.coverContainer}>
          <Image source={{ uri: book.coverImage }} style={styles.coverImage} />
          <View style={styles.coverShadow} />
        </View>

        {/* Book Information */}
        <View style={styles.infoContainer}>
          <Text style={styles.title}>{book.title}</Text>
          <Text style={styles.author}>by {book.author}</Text>

          {/* Rating and Metadata */}
          <View style={styles.metadataContainer}>
            <View style={styles.ratingContainer}>
              <Star size={20} color="#fbbf24" fill="#fbbf24" />
              <Text style={styles.ratingText}>{book.rating}</Text>
              <Text style={styles.ratingSubtext}>rating</Text>
            </View>
            
            <View style={styles.metadataItem}>
              <Calendar size={16} color="#6b7280" />
              <Text style={styles.metadataText}>{book.publicationYear}</Text>
            </View>
            
            <View style={styles.metadataItem}>
              <BookOpen size={16} color="#6b7280" />
              <Text style={styles.metadataText}>{book.pages} pages</Text>
            </View>
          </View>

          {/* Genre and ISBN */}
          <View style={styles.additionalInfo}>
            <View style={styles.genreContainer}>
              <Text style={styles.genreText}>{book.genre}</Text>
            </View>
            <View style={styles.isbnContainer}>
              <Hash size={14} color="#6b7280" />
              <Text style={styles.isbnText}>{book.isbn}</Text>
            </View>
          </View>

          {/* Description */}
          <View style={styles.descriptionContainer}>
            <Text style={styles.descriptionTitle}>Synopsis</Text>
            <Text style={styles.descriptionText}>{book.description}</Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#1f2937',
  },
  headerButton: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    flex: 1,
    fontSize: 18,
    fontWeight: '600',
    color: '#ffffff',
    textAlign: 'center',
    marginHorizontal: 16,
  },
  scrollView: {
    flex: 1,
  },
  coverContainer: {
    alignItems: 'center',
    paddingTop: 32,
    paddingBottom: 24,
    backgroundColor: '#ffffff',
  },
  coverImage: {
    width: width * 0.6,
    height: width * 0.9,
    borderRadius: 16,
    backgroundColor: '#e5e7eb',
  },
  coverShadow: {
    position: 'absolute',
    top: 36,
    left: width * 0.22,
    right: width * 0.22,
    height: width * 0.9,
    backgroundColor: '#000',
    opacity: 0.15,
    borderRadius: 16,
    zIndex: -1,
  },
  infoContainer: {
    backgroundColor: '#ffffff',
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#1f2937',
    lineHeight: 34,
    marginBottom: 8,
  },
  author: {
    fontSize: 18,
    fontStyle: 'italic',
    color: '#6b7280',
    marginBottom: 24,
  },
  metadataContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
    flexWrap: 'wrap',
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 24,
    marginBottom: 8,
  },
  ratingText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1f2937',
    marginLeft: 6,
  },
  ratingSubtext: {
    fontSize: 14,
    color: '#6b7280',
    marginLeft: 4,
  },
  metadataItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 20,
    marginBottom: 8,
  },
  metadataText: {
    fontSize: 14,
    color: '#6b7280',
    marginLeft: 6,
    fontWeight: '500',
  },
  additionalInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 32,
  },
  genreContainer: {
    backgroundColor: '#dbeafe',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  genreText: {
    fontSize: 14,
    color: '#1d4ed8',
    fontWeight: '600',
  },
  isbnContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  isbnText: {
    fontSize: 12,
    color: '#9ca3af',
    fontFamily: 'monospace',
    marginLeft: 4,
  },
  descriptionContainer: {
    marginTop: 8,
  },
  descriptionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: 16,
  },
  descriptionText: {
    fontSize: 16,
    color: '#374151',
    lineHeight: 24,
    textAlign: 'justify',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  errorText: {
    fontSize: 18,
    color: '#ef4444',
    marginBottom: 24,
  },
  backButton: {
    backgroundColor: '#3b82f6',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  backButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});