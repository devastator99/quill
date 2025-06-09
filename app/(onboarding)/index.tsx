import React, { useState, useRef } from 'react';
import { View, ScrollView, StyleSheet, Dimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import OnboardingSlide from '@/components/OnboardingSlide';
import AuthButton from '@/components/AuthButton';
import { colors, spacing } from '@/styles/theme';
import { storage, STORAGE_KEYS } from '@/utils/storage';

const { width } = Dimensions.get('window');

const slides = [
  {
    image: 'https://images.pexels.com/photos/5483077/pexels-photo-5483077.jpeg?auto=compress&cs=tinysrgb&w=800',
    title: 'Welcome to ChatAI',
    description: 'Experience the power of AI conversations with our advanced chatbot technology.',
  },
  {
    image: 'https://images.pexels.com/photos/8386440/pexels-photo-8386440.jpeg?auto=compress&cs=tinysrgb&w=800',
    title: 'Smart Conversations',
    description: 'Get instant answers, creative ideas, and helpful assistance for any topic.',
  },
  {
    image: 'https://images.pexels.com/photos/5483064/pexels-photo-5483064.jpeg?auto=compress&cs=tinysrgb&w=800',
    title: 'Always Available',
    description: 'Your AI assistant is ready 24/7 to help you with questions and tasks.',
  },
];

export default function OnboardingScreen() {
  const [currentSlide, setCurrentSlide] = useState(0);
  const scrollViewRef = useRef<ScrollView>(null);
  const router = useRouter();

  const handleScroll = (event: any) => {
    const slideIndex = Math.round(event.nativeEvent.contentOffset.x / width);
    setCurrentSlide(slideIndex);
  };

  const handleGetStarted = async () => {
    await storage.setBool(STORAGE_KEYS.HAS_SEEN_ONBOARDING, true);
    router.replace('/(auth)/login');
  };

  const renderPagination = () => (
    <View style={styles.paginationContainer}>
      {slides.map((_, index) => (
        <View
          key={index}
          style={[
            styles.paginationDot,
            index === currentSlide ? styles.paginationDotActive : null,
          ]}
        />
      ))}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        ref={scrollViewRef}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={handleScroll}
        scrollEventThrottle={16}
      >
        {slides.map((slide, index) => (
          <OnboardingSlide
            key={index}
            image={slide.image}
            title={slide.title}
            description={slide.description}
          />
        ))}
      </ScrollView>

      {renderPagination()}

      <View style={styles.buttonContainer}>
        <AuthButton
          title="Get Started"
          onPress={handleGetStarted}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  paginationContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: spacing.lg,
  },
  paginationDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.border,
    marginHorizontal: 4,
  },
  paginationDotActive: {
    width: 24,
    backgroundColor: colors.primary,
  },
  buttonContainer: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
  },
});