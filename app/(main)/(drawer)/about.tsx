import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { BookOpen, Heart, Code } from 'lucide-react-native';

export default function AboutScreen() {
  return (
    <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
      <View style={styles.headerSection}>
        <View style={styles.iconContainer}>
          <BookOpen size={48} color="#3b82f6" />
        </View>
        <Text style={styles.appTitle}>Book Catalog</Text>
        <Text style={styles.version}>Version 1.0.0</Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About This App</Text>
        <Text style={styles.description}>
          Book Catalog is a beautiful and intuitive mobile application designed for book lovers. 
          Discover, explore, and organize your reading journey with our carefully curated collection 
          of books across various genres.
        </Text>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Features</Text>
        <View style={styles.featureList}>
          <View style={styles.featureItem}>
            <Text style={styles.featureBullet}>•</Text>
            <Text style={styles.featureText}>Browse extensive book catalog</Text>
          </View>
          <View style={styles.featureItem}>
            <Text style={styles.featureBullet}>•</Text>
            <Text style={styles.featureText}>Search by title, author, or genre</Text>
          </View>
          <View style={styles.featureItem}>
            <Text style={styles.featureBullet}>•</Text>
            <Text style={styles.featureText}>Detailed book information and ratings</Text>
          </View>
          <View style={styles.featureItem}>
            <Text style={styles.featureBullet}>•</Text>
            <Text style={styles.featureText}>Clean and intuitive interface</Text>
          </View>
          <View style={styles.featureItem}>
            <Text style={styles.featureBullet}>•</Text>
            <Text style={styles.featureText}>Responsive design for all devices</Text>
          </View>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Built With</Text>
        <View style={styles.techStack}>
          <View style={styles.techItem}>
            <Code size={20} color="#6b7280" />
            <Text style={styles.techText}>React Native</Text>
          </View>
          <View style={styles.techItem}>
            <Code size={20} color="#6b7280" />
            <Text style={styles.techText}>Expo Router</Text>
          </View>
          <View style={styles.techItem}>
            <Code size={20} color="#6b7280" />
            <Text style={styles.techText}>TypeScript</Text>
          </View>
        </View>
      </View>

      <View style={styles.footer}>
        <Heart size={16} color="#ef4444" fill="#ef4444" />
        <Text style={styles.footerText}>Made with love for book enthusiasts</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollView: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  content: {
    padding: 24,
  },
  headerSection: {
    alignItems: 'center',
    marginBottom: 40,
    paddingVertical: 24,
  },
  iconContainer: {
    width: 80,
    height: 80,
    backgroundColor: '#dbeafe',
    borderRadius: 40,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  appTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: 8,
    fontFamily: "Urbanist_600SemiBold",
  },
  version: {
    fontSize: 16,
    color: '#6b7280',
    fontWeight: '500',
    fontFamily: "Urbanist_400Regular",
  },
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: 16,
  },
  description: {
    fontSize: 16,
    color: '#374151',
    lineHeight: 24,
    textAlign: 'justify',
  },
  featureList: {
    marginTop: 8,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  featureBullet: {
    fontSize: 16,
    color: '#3b82f6',
    fontWeight: '700',
    marginRight: 12,
    marginTop: 2,
  },
  featureText: {
    fontSize: 16,
    color: '#374151',
    flex: 1,
    lineHeight: 22,
  },
  techStack: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 8,
  },
  techItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    marginRight: 12,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  techText: {
    fontSize: 14,
    color: '#374151',
    fontWeight: '500',
    marginLeft: 6,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 24,
    paddingTop: 24,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  footerText: {
    fontSize: 14,
    fontFamily: "Urbanist_400Regular",
    color: '#6b7280',
    marginLeft: 8,
    fontStyle: 'italic',
  },
});