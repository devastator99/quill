// BooksScreen.tsx

import React, { useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  Image,
  StyleSheet,
  TextInput,
  SafeAreaView,
  StatusBar,
  Dimensions,
} from 'react-native';
import { router } from 'expo-router';
import { Search, Star } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import {
  useFonts,
  Urbanist_400Regular,
  Urbanist_600SemiBold,
  Urbanist_500Medium,
} from '@expo-google-fonts/urbanist';
import BookCard from '@/components/BookCard';

// Example data & type — replace with your real imports
interface Book {
  id: string;
  title: string;
  author: string;
  coverImage: string;
  genre: string;
  rating: number;
  publicationYear: number;
  /** Fraction read, 0–1 */
  progress?: number;
}

import { booksData } from '@/data/books'; // your actual data

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = SCREEN_WIDTH * 0.7;
const GRID_ITEM_WIDTH = (SCREEN_WIDTH - 48) / 2; // 16px padding + 16px gap

export default function BooksScreen() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredBooks, setFilteredBooks] = useState<Book[]>(booksData);

  // Only those with 0 < progress < 1
  const continueReading = booksData.filter(
    (b) => b.progress !== undefined && b.progress > 0 && b.progress < 1
  );

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (!query.trim()) return setFilteredBooks(booksData);
    const q = query.toLowerCase();
    setFilteredBooks(
      booksData.filter(
        (b) =>
          b.title.toLowerCase().includes(q) ||
          b.author.toLowerCase().includes(q) ||
          b.genre.toLowerCase().includes(q)
      )
    );
  };

  const navigateToBookDetails = (bookId: string) =>
    router.push(`/books/${bookId}`);

  const renderContinueCard = ({ item }: { item: Book }) => {
    const percent = Math.round((item.progress || 0) * 100);
    return (
      <TouchableOpacity
        style={styles.continueCard}
        onPress={() => navigateToBookDetails(item.id)}
        activeOpacity={0.8}
      >
        <Image source={{ uri: item.coverImage }} style={styles.continueCover} />
        <LinearGradient
          colors={['transparent', 'rgba(0,0,0,0.6)']}
          style={styles.continueOverlay}
        >
          <Text style={styles.continueTitle} numberOfLines={1}>
            {item.title}
          </Text>
          <View style={styles.progressBarContainer}>
            <View style={[styles.progressBarFill, { width: `${percent}%` }]} />
          </View>
          <Text style={styles.progressLabel}>{percent}% read</Text>
        </LinearGradient>
      </TouchableOpacity>
    );
  };

  const renderBookCard = ({ item }: { item: Book }) => (
    <BookCard
      id={item.id}
      coverUri={item.coverImage}
      title={item.title}
      author={item.author}
      rating={item.rating}
      year={item.publicationYear}
      onPress={navigateToBookDetails}
    />
  );

  const [fontsLoaded] = useFonts({
    Urbanist_400Regular,
    Urbanist_500Medium,
    Urbanist_600SemiBold,
  });
  if (!fontsLoaded) return null;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#1f2937" />

      {/* Search */}
      <View style={styles.searchContainer}>
        <View style={styles.searchInputContainer}>
          <Search size={20} color="#6b7280" />
          <TextInput
            style={styles.searchInput}
            placeholder="Search books, authors, genres..."
            placeholderTextColor="#9ca3af"
            value={searchQuery}
            onChangeText={handleSearch}
          />
        </View>
      </View>

      {/* Continue Reading */}
      {continueReading.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionHeader}>Continue Reading</Text>
          <FlatList
            data={continueReading}
            horizontal
            showsHorizontalScrollIndicator={false}
            keyExtractor={(b) => b.id}
            renderItem={renderContinueCard}
            contentContainerStyle={{ paddingHorizontal: 16 }}
            ItemSeparatorComponent={() => <View style={{ width: 16 }} />}
          />
        </View>
      )}

      {/* Featured Grid */}
      <View style={styles.section}>
        <View style={styles.featuredHeader}>
          <Text style={styles.sectionHeader}>
            {searchQuery
              ? `Results for "${searchQuery}"`
              : 'Featured Books'}
          </Text>
          <Text style={styles.countText}>
            {filteredBooks.length}{' '}
            {filteredBooks.length === 1 ? 'book' : 'books'}
          </Text>
        </View>
        <FlatList
          data={filteredBooks}
          renderItem={renderBookCard}
          keyExtractor={(item) => item.id}
          numColumns={2}
          columnWrapperStyle={styles.gridRow}
          contentContainerStyle={{ paddingBottom: 24, paddingTop: 8 }}
          showsVerticalScrollIndicator={false}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },

  // Search
  searchContainer: {
    padding: 16,
    backgroundColor: '#fff',
    borderBottomColor: '#e5e7eb',
    borderBottomWidth: 1,
  },
  searchInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f3f4f6',
    borderRadius: 12,
    padding: 10,
  },
  searchInput: {
    flex: 1,
    marginLeft: 8,
    fontSize: 16,
    color: '#1f2937',
    fontFamily: 'Urbanist_400Regular',
  },

  // Sections
  section: {
    marginTop: 12,
  },
  sectionHeader: {
    marginHorizontal: 16,
    fontSize: 20,
    fontFamily: 'Urbanist_600SemiBold',
    color: '#1f2937',
    marginBottom: 8,
  },
  featuredHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginHorizontal: 16,
  },
  countText: {
    fontSize: 14,
    fontFamily: 'Urbanist_500Medium',
    color: '#6b7280',
  },

  // Continue Reading Cards
  continueCard: {
    width: CARD_WIDTH,
    height: CARD_WIDTH * 1.4,
    borderRadius: 16,
    overflow: 'hidden',
  },
  continueCover: {
    ...StyleSheet.absoluteFillObject,
    resizeMode: 'cover',
  },
  continueOverlay: {
    position: 'absolute',
    bottom: 0,
    width: '100%',
    padding: 12,
  },
  continueTitle: {
    color: '#fff',
    fontSize: 16,
    fontFamily: 'Urbanist_600SemiBold',
    marginBottom: 6,
  },
  progressBarContainer: {
    height: 4,
    width: '100%',
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: 4,
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: '#22c55e',
  },
  progressLabel: {
    color: '#e5e5e5',
    fontSize: 12,
    fontFamily: 'Urbanist_400Regular',
  },

  // Featured Grid Cards
  gridRow: {
    justifyContent: 'space-between',
    marginHorizontal: 16,
  },
  gridCard: {
    width: GRID_ITEM_WIDTH,
    marginBottom: 24,
    borderRadius: 16,
    overflow: 'hidden',
    backgroundColor: '#fff',
    elevation: 3,
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 8,
  },
  gridCover: {
    width: '100%',
    height: GRID_ITEM_WIDTH * 1.5,
  },
  gridOverlay: {
    position: 'absolute',
    bottom: 0,
    width: '100%',
    padding: 8,
  },
  gridTitle: {
    color: '#fff',
    fontSize: 14,
    fontFamily: 'Urbanist_600SemiBold',
  },
  gridMeta: {
    padding: 12,
  },
  gridAuthor: {
    fontSize: 12,
    fontFamily: 'Urbanist_500Medium',
    color: '#6b7280',
    marginBottom: 4,
  },
  gridInfoRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  gridRating: {
    marginLeft: 4,
    marginRight: 8,
    fontSize: 12,
    fontFamily: 'Urbanist_500Medium',
    color: '#1f2937',
  },
  gridYear: {
    fontSize: 12,
    fontFamily: 'Urbanist_400Regular',
    color: '#9ca3af',
  },
});
