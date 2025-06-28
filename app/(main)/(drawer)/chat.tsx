// ChatScreen.js

import React, { useState, useEffect } from "react";
import { View, FlatList, StyleSheet, KeyboardAvoidingView, Platform, Keyboard, Alert } from "react-native";
import { SafeAreaProvider , SafeAreaView} from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { StatusBar } from "expo-status-bar";
import axios from "axios";

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

// Replace with your actual backend URL
const BACKEND_URL = 'http://localhost:8000'; // Update this to your backend URL

interface Message {
  id: string;
  type: 'preview' | 'response';
  avatar: any;
  text: string;
  sources?: string[];
  isLoading?: boolean;
}

const initialMessages: Message[] = [
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
];

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [inputText, setInputText] = useState("");
  const [keyboardHeight, setKeyboardHeight] = useState(0);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

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

  const sendMessageToAPI = async (message: string) => {
    try {
      const payload: any = {
        message: message,
      };
      
      // Only include conversation_id if it exists
      if (conversationId) {
        payload.conversation_id = conversationId;
      }
      
      const response = await axios.post(`${BACKEND_URL}/chat/`, payload);

      return response.data;
    } catch (error: any) {
      console.error('Chat API error:', error);
      throw new Error(error.response?.data?.detail || 'Failed to get response from AI');
    }
  };

  const handleEdit = (id: any) => console.log("Edit message", id);
  
  const handleSend = async () => {
    if (!inputText.trim() || isLoading) return;
    
    const userMessage: Message = {
      id: String(Date.now()),
      type: "preview",
      avatar: require("@/assets/user.png"),
      text: inputText.trim(),
    };

    // Add user message immediately
    setMessages((prev) => [...prev, userMessage]);
    const currentInput = inputText.trim();
    setInputText("");
    setIsLoading(true);

    // Add loading message
    const loadingMessage: Message = {
      id: String(Date.now() + 1),
      type: "response",
      avatar: require("@/assets/robot.png"),
      text: "Thinking...",
      isLoading: true,
    };
    setMessages((prev) => [...prev, loadingMessage]);

    try {
      // Send message to API
      const apiResponse = await sendMessageToAPI(currentInput);
      
      // Update conversation ID if it's a new conversation
      if (!conversationId && apiResponse.conversation_id) {
        setConversationId(apiResponse.conversation_id);
      }

      // Replace loading message with actual response
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === loadingMessage.id 
            ? {
                ...msg,
                text: apiResponse.response,
                sources: apiResponse.sources,
                isLoading: false,
              }
            : msg
        )
      );
    } catch (error: any) {
      // Replace loading message with error message
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === loadingMessage.id 
            ? {
                ...msg,
                text: "I'm sorry, I encountered an error while processing your request. Please try again.",
                isLoading: false,
              }
            : msg
        )
      );
      
      Alert.alert('Error', error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerate = async () => {
    if (messages.length < 2) return;
    
    // Find the last user message
    const lastUserMessage = [...messages].reverse().find(msg => msg.type === 'preview');
    if (!lastUserMessage) return;

    setIsLoading(true);

    // Add loading message
    const loadingMessage: Message = {
      id: String(Date.now()),
      type: "response",
      avatar: require("@/assets/robot.png"),
      text: "Regenerating response...",
      isLoading: true,
    };
    setMessages((prev) => [...prev, loadingMessage]);

    try {
      // Send the last user message to API again
      const apiResponse = await sendMessageToAPI(lastUserMessage.text);
      
      // Replace loading message with new response
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === loadingMessage.id 
            ? {
                ...msg,
                text: apiResponse.response,
                sources: apiResponse.sources,
                isLoading: false,
              }
            : msg
        )
      );
    } catch (error: any) {
      // Remove loading message on error
      setMessages((prev) => prev.filter(msg => msg.id !== loadingMessage.id));
      Alert.alert('Error', error.message);
    } finally {
      setIsLoading(false);
    }
  };

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
        <Header title="AI Chat" onBack={() => {}} onMenu={() => {}} />

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
                <ResponseBubble 
                  avatar={item.avatar} 
                  text={item.text}
                  sources={item.sources}
                  isLoading={item.isLoading}
                />
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
          disabled={isLoading}
        />
        <InputBar
          value={inputText}
          onChangeText={setInputText}
          onSend={handleSend}
          onMic={() => console.log("Mic tapped")}
          style={dynamicStyles.floatingInput}
          disabled={isLoading}
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
