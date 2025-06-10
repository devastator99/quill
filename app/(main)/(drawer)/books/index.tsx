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
} from 'react-native';
import { router } from 'expo-router';
import { Search, Star } from 'lucide-react-native';
import { booksData } from '@/data/books';
import { Book } from '@/types/book';

export default function BooksScreen() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredBooks, setFilteredBooks] = useState(booksData);

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (query.trim() === '') {
      setFilteredBooks(booksData);
    } else {
      const filtered = booksData.filter(book =>
        book.title.toLowerCase().includes(query.toLowerCase()) ||
        book.author.toLowerCase().includes(query.toLowerCase()) ||
        book.genre.toLowerCase().includes(query.toLowerCase())
      );
      setFilteredBooks(filtered);
    }
  };

  const navigateToBookDetails = (book: Book) => {
    router.push(`/books/${book.id}`);
  };

  const renderBookCard = ({ item }: { item: Book }) => (
    <TouchableOpacity
      style={styles.bookCard}
      onPress={() => navigateToBookDetails(item)}
      activeOpacity={0.8}>
      <Image source={{ uri: item.coverImage }} style={styles.bookCover} />
      <View style={styles.bookInfo}>
        <Text style={styles.bookTitle} numberOfLines={2}>
          {item.title}
        </Text>
        <Text style={styles.bookAuthor} numberOfLines={1}>
          {item.author}
        </Text>
        <View style={styles.bookMeta}>
          <View style={styles.ratingContainer}>
            <Star size={14} color="#fbbf24" fill="#fbbf24" />
            <Text style={styles.rating}>{item.rating}</Text>
          </View>
          <Text style={styles.genre}>{item.genre}</Text>
        </View>
        <Text style={styles.year}>{item.publicationYear}</Text>
      </View>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#1f2937" />
      
      <View style={styles.searchContainer}>
        <View style={styles.searchInputContainer}>
          <Search size={20} color="#6b7280" style={styles.searchIcon} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search books, authors, genres..."
            placeholderTextColor="#9ca3af"
            value={searchQuery}
            onChangeText={handleSearch}
          />
        </View>
      </View>

      <View style={styles.headerContainer}>
        <Text style={styles.sectionTitle}>
          {searchQuery ? `Results for "${searchQuery}"` : 'Featured Books'}
        </Text>
        <Text style={styles.bookCount}>
          {filteredBooks.length} {filteredBooks.length === 1 ? 'book' : 'books'}
        </Text>
      </View>

      <FlatList
        data={filteredBooks}
        renderItem={renderBookCard}
        keyExtractor={(item) => item.id}
        numColumns={2}
        columnWrapperStyle={styles.row}
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  searchContainer: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  searchInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f3f4f6',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    color: '#1f2937',
  },
  headerContainer: {
    paddingHorizontal: 16,
    paddingVertical: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1f2937',
  },
  bookCount: {
    fontSize: 14,
    color: '#6b7280',
    fontWeight: '500',
  },
  listContainer: {
    paddingHorizontal: 8,
    paddingBottom: 24,
  },
  row: {
    justifyContent: 'space-between',
    paddingHorizontal: 8,
  },
  separator: {
    height: 16,
  },
  bookCard: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 12,
    margin: 8,
    flex: 0.48,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  bookCover: {
    width: '100%',
    height: 200,
    borderRadius: 12,
    marginBottom: 12,
    backgroundColor: '#e5e7eb',
  },
  bookInfo: {
    flex: 1,
  },
  bookTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: 4,
    lineHeight: 20,
  },
  bookAuthor: {
    fontSize: 14,
    fontStyle: 'italic',
    color: '#6b7280',
    marginBottom: 8,
  },
  bookMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  rating: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1f2937',
    marginLeft: 4,
  },
  genre: {
    fontSize: 12,
    color: '#3b82f6',
    fontWeight: '500',
  },
  year: {
    fontSize: 12,
    color: '#9ca3af',
    fontWeight: '400',
  },
});