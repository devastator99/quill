import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import AuthButton from '@/components/AuthButton';
import { colors, typography, spacing, commonStyles } from '@/styles/theme';

const plans = [
  {
    id: 'monthly',
    title: 'Monthly',
    price: '$9.99',
    period: '/month',
    popular: false,
  },
  {
    id: 'yearly',
    title: 'Yearly',
    price: '$99.99',
    period: '/year',
    popular: true,
    savings: 'Save 17%',
  },
];

const features = [
  'Unlimited AI conversations',
  'Priority response times',
  'Advanced AI models access',
  'Custom conversation templates',
  'Export chat history',
  '24/7 Premium support',
];

export default function PurchasePremiumScreen() {
  const [selectedPlan, setSelectedPlan] = useState('yearly');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handlePurchase = async () => {
    setLoading(true);
    
    // Simulate purchase process
    setTimeout(() => {
      setLoading(false);
      Alert.alert(
        'Purchase Successful!',
        'Welcome to ChatAI Premium! You now have access to all premium features.',
        [{ text: 'OK', onPress: () => router.back() }]
      );
    }, 2000);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.closeButton}>
          <Ionicons name="close" size={24} color={colors.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Go Premium</Text>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        <LinearGradient
          colors={[colors.primary, colors.primaryDark]}
          style={styles.heroSection}
        >
          <Ionicons name="star" size={48} color={colors.textLight} />
          <Text style={styles.heroTitle}>Unlock Premium Features</Text>
          <Text style={styles.heroSubtitle}>
            Get the most out of your AI conversations
          </Text>
        </LinearGradient>

        <View style={styles.featuresSection}>
          <Text style={styles.sectionTitle}>Premium Features</Text>
          {features.map((feature, index) => (
            <View key={index} style={styles.featureItem}>
              <Ionicons name="checkmark-circle" size={20} color={colors.success} />
              <Text style={styles.featureText}>{feature}</Text>
            </View>
          ))}
        </View>

        <View style={styles.plansSection}>
          <Text style={styles.sectionTitle}>Choose Your Plan</Text>
          {plans.map((plan) => (
            <TouchableOpacity
              key={plan.id}
              style={[
                styles.planItem,
                selectedPlan === plan.id && styles.planItemSelected,
              ]}
              onPress={() => setSelectedPlan(plan.id)}
            >
              {plan.popular && (
                <View style={styles.popularBadge}>
                  <Text style={styles.popularBadgeText}>Most Popular</Text>
                </View>
              )}
              
              <View style={styles.planContent}>
                <View style={styles.planLeft}>
                  <Text style={styles.planTitle}>{plan.title}</Text>
                  {plan.savings && (
                    <Text style={styles.planSavings}>{plan.savings}</Text>
                  )}
                </View>
                
                <View style={styles.planRight}>
                  <Text style={styles.planPrice}>{plan.price}</Text>
                  <Text style={styles.planPeriod}>{plan.period}</Text>
                </View>
              </View>
              
              <View style={[
                styles.radioButton,
                selectedPlan === plan.id && styles.radioButtonSelected,
              ]}>
                {selectedPlan === plan.id && (
                  <View style={styles.radioButtonInner} />
                )}
              </View>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.buttonSection}>
          <AuthButton
            title="Start Premium Subscription"
            onPress={handlePurchase}
            loading={loading}
          />
          
          <Text style={styles.disclaimer}>
            Cancel anytime. No commitments, no cancellation fees.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    ...commonStyles.container,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  closeButton: {
    position: 'absolute',
    left: spacing.lg,
  },
  headerTitle: {
    ...typography.h3,
    color: colors.text,
  },
  content: {
    flex: 1,
  },
  heroSection: {
    alignItems: 'center',
    paddingVertical: spacing.xxl,
    marginBottom: spacing.lg,
  },
  heroTitle: {
    ...typography.h2,
    color: colors.textLight,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
  heroSubtitle: {
    ...typography.body,
    color: colors.textLight,
    opacity: 0.9,
    textAlign: 'center',
  },
  featuresSection: {
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.lg,
  },
  sectionTitle: {
    ...typography.h3,
    color: colors.text,
    marginBottom: spacing.md,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  featureText: {
    ...typography.body,
    color: colors.text,
    marginLeft: spacing.sm,
  },
  plansSection: {
    paddingHorizontal: spacing.lg,
    marginBottom: spacing.lg,
  },
  planItem: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 2,
    borderColor: colors.border,
    position: 'relative',
  },
  planItemSelected: {
    borderColor: colors.primary,
    backgroundColor: colors.primary + '10',
  },
  popularBadge: {
    position: 'absolute',
    top: -8,
    right: spacing.md,
    backgroundColor: colors.accent,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: 12,
  },
  popularBadgeText: {
    ...typography.caption,
    color: colors.textLight,
    fontWeight: '600',
  },
  planContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  planLeft: {
    flex: 1,
  },
  planTitle: {
    ...typography.h3,
    color: colors.text,
  },
  planSavings: {
    ...typography.bodySmall,
    color: colors.success,
    fontWeight: '600',
  },
  planRight: {
    alignItems: 'flex-end',
  },
  planPrice: {
    ...typography.h3,
    color: colors.text,
  },
  planPeriod: {
    ...typography.bodySmall,
    color: colors.textSecondary,
  },
  radioButton: {
    position: 'absolute',
    top: spacing.md,
    right: spacing.md,
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  radioButtonSelected: {
    borderColor: colors.primary,
  },
  radioButtonInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.primary,
  },
  buttonSection: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
  },
  disclaimer: {
    ...typography.bodySmall,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: spacing.md,
  },
});