// ChatScreen.js

import React, { useState, useEffect } from "react";
import { View, FlatList, StyleSheet, KeyboardAvoidingView, Platform, Keyboard } from "react-native";
import { SafeAreaProvider , SafeAreaView} from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { StatusBar } from "expo-status-bar";

import Header from "@/components/Header";
import PreviewBubble from "@/components/PreviewBubble";
import ResponseBubble from "@/components/ResponseBubble";
import RegenerateButton from "@/components/RegenerateButton";
import InputBar from "@/components/InputBar";

import {
  useFonts,
  Urbanist_400Regular,
  Urbanist_600SemiBold,
  Urbanist_500Medium,
  Urbanist_400Regular_Italic,
} from "@expo-google-fonts/urbanist";

const initialMessages = [
  {
    id: "1",
    type: "preview",
    avatar: require("@/assets/user.png"),
    text: "Natural Foods for Cancer patience",
  },
  {
    id: "2",
    type: "response",
    avatar: require("@/assets/robot.png"),
    text:
      "A diet rich in natural foods can be beneficial for cancer patients. Here are some natural foods that you may consider:\n\n" +
      "• Leafy green vegetables – spinach, kale, collard greens, and others are packed with vitamins, minerals, and antioxidants that can help to boost the immune system and fight cancer.",
  },
  {
    id: "3",
    type: "preview",
    avatar: require("@/assets/user.png"),
    text: "tell me head pain medicines",
  },
  {
    id: "4",
    type: "response",
    avatar: require("@/assets/robot.png"),
    text:
      "There are several over-the-counter and prescription medications that can be used to treat head pain. Some common ones include:\n\n" +
      "• Acetaminophen (Tylenol) – This is an over-the-counter medication that can be effective for mild to moderate headaches.",
  },
  {
    id: "5",
    type: "preview",
    avatar: require("@/assets/user.png"),
    text: "what are early symptoms of diabetes",
  },
  {
    id: "6",
    type: "response",
    avatar: require("@/assets/robot.png"),
    text:
      "Early symptoms of diabetes can include:\n\n" +
      "• Increased thirst and frequent urination – excess sugar in your blood pulls water from tissues.\n" +
      "• Unexplained weight loss – your body starts burning fat and muscle for energy.\n" +
      "• Fatigue – lack of sugar getting into your cells can make you tired and weak.\n" +
      "• Blurred vision – high blood sugar can pull fluid from your lenses, affecting focus.\n" +
      "• Slow-healing sores or frequent infections – high glucose levels can impair circulation and immune function.",
  },
  {
    id: "7",
    type: "preview",
    avatar: require("@/assets/user.png"),
    text: "suggest exercises for weight loss",
  },
  {
    id: "8",
    type: "response",
    avatar: require("@/assets/robot.png"),
    text:
      "Here are some exercises effective for weight loss:\n\n" +
      "• High-Intensity Interval Training (HIIT) – short bursts of intense activity followed by rest.\n" +
      "• Brisk walking or jogging – aim for 30–45 minutes most days.\n" +
      "• Strength training – weight lifting or bodyweight exercises 2–3× per week to build muscle.\n" +
      "• Cycling – either stationary or outdoor, maintain moderate effort for 45–60 minutes.\n" +
      "• Swimming – full-body workout with low impact, 30–60 minutes sessions.",
  },
  {
    id: "9",
    type: "preview",
    avatar: require("@/assets/user.png"),
    text: "how to improve sleep quality",
  },
  {
    id: "10",
    type: "response",
    avatar: require("@/assets/robot.png"),
    text:
      "To improve sleep quality, consider:\n\n" +
      "• Maintaining a consistent sleep schedule – go to bed and wake up at the same times each day.\n" +
      "• Creating a relaxing bedtime routine – read, meditate, or take a warm bath.\n" +
      "• Optimizing your sleep environment – cool, dark, and quiet room; comfortable mattress and pillows.\n" +
      "• Limiting screen time before bed – avoid blue light at least 1 hour before sleep.\n" +
      "• Reducing caffeine and heavy meals in the evening – opt for light, easily digestible snacks if needed.",
  },
];

export default function ChatScreen() {
  const [messages, setMessages] = useState(initialMessages);
  const [inputText, setInputText] = useState("");
  const [keyboardHeight, setKeyboardHeight] = useState(0);

  const [fontsLoaded] = useFonts({
    Urbanist_400Regular,
    Urbanist_600SemiBold,
    Urbanist_500Medium,
    Urbanist_400Regular_Italic,
  });

  useEffect(() => {
    const keyboardDidShowListener = Keyboard.addListener(
      'keyboardDidShow',
      (e) => setKeyboardHeight(e.endCoordinates.height)
    );
    const keyboardDidHideListener = Keyboard.addListener(
      'keyboardDidHide',
      () => setKeyboardHeight(0)
    );

    return () => {
      keyboardDidShowListener?.remove();
      keyboardDidHideListener?.remove();
    };
  }, []);

  if (!fontsLoaded) return null;

  const handleEdit = (id: any) => console.log("Edit message", id);
  const handleSend = () => {
    if (!inputText.trim()) return;
    setMessages((m) => [
      ...m,
      {
        id: String(m.length + 1),
        type: "preview",
        avatar: require("@/assets/user.png"),
        text: inputText.trim(),
      },
    ]);
    setInputText("");
  };
  const handleRegenerate = () => console.log("Regenerate!");

  const dynamicStyles = {
    floatingButton: {
      position: "absolute" as const,
      bottom: keyboardHeight > 0 ? keyboardHeight + 140 : 130,
      alignSelf: "center" as const,
      backgroundColor: "#e6e6e6",
      paddingHorizontal: 8,
      paddingVertical: 6,
      borderRadius: 4,
      shadowColor: "#000",
      shadowOffset: { width: 2, height: 2 },
      shadowOpacity: 0.3,
      shadowRadius: 5,
      elevation: 4,
      zIndex: 10,
    },
    floatingInput: {
      position: "absolute" as const,
      bottom: keyboardHeight > 0 ? keyboardHeight + 80 : 70,
      alignSelf: "center" as const,
      zIndex: 10,
      elevation: 6,
    },
  };

  return (
      <SafeAreaView style={styles.container}>
        <StatusBar style="dark" />
        <Header title="Books" onBack={() => {}} onMenu={() => {}} />

        <View style={styles.listWrapper}>
          <FlatList
            data={messages}
            keyExtractor={(i) => i.id}
            contentContainerStyle={{
              paddingVertical: 16,
              paddingBottom: 140,
            }}
            renderItem={({ item }) =>
              item.type === "preview" ? (
                <PreviewBubble
                  avatar={item.avatar}
                  question={item.text}
                  onEdit={() => handleEdit(item.id)}
                />
              ) : (
                <ResponseBubble avatar={item.avatar} text={item.text} />
              )
            }
          />

          <LinearGradient
            pointerEvents="none"
            colors={["rgba(255, 255, 255, 0.7)", "rgba(255, 255, 255, 0.29)"]}
            style={styles.topFade}
            start={{ x: 0, y: 0 }}
            end={{ x: 0, y: 1 }}
          />

          <LinearGradient
            pointerEvents="none"
            colors={["transparent", "rgba(0,0,0,0.7)"]}
            style={styles.bottomFade}
            start={{ x: 0, y: 0 }}
            end={{ x: 0, y: 1 }}
          />
        </View>

        <RegenerateButton
          onPress={handleRegenerate}
          style={dynamicStyles.floatingButton}
        />
        <InputBar
          value={inputText}
          onChangeText={setInputText}
          onSend={handleSend}
          onMic={() => console.log("Mic tapped")}
          style={dynamicStyles.floatingInput}
        />
      </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: -32,
  },
  listWrapper: {
    flex: 1,
    position: "relative",
  },
  topFade: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    height: 25,
    zIndex: 5,
  },
  bottomFade: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    height: 100,
    zIndex: 5,
  },
  floatingButton: {
    position: "absolute",
    bottom: 130,
    alignSelf: "center",
    backgroundColor: "#e6e6e6",
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: 4,
    shadowColor: "#000",
    shadowOffset: { width: 2, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
    elevation: 4,
    zIndex: 10,
  },
  floatingInput: {
    position: "absolute",
    bottom: 70,
    alignSelf: "center",
    zIndex: 10,
    elevation: 6,
  },
});
