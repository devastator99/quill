import React from "react";
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  Share,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Clipboard from "expo-clipboard";
import { ImageSourcePropType } from "react-native";
import ShadowContainer from "./ShadowContainer";

export default function ResponseBubble({
  avatar,
  text,
  sources,
  isLoading,
}: {
  avatar: ImageSourcePropType;
  text: string;
  sources?: string[];
  isLoading?: boolean;
}) {
  const handleCopy = () => Clipboard.setString(text);
  const handleShare = () => {
    Share.share({ message: text });
  };

  return (
    <View style={styles.container}>
      {/* Top row: avatar on left, icons on right */}
      <View style={styles.topRow}>
        <ShadowContainer
          imageSource={avatar}
          imageStyle={styles.avatar}
          containerStyle={styles.shadow}
        />

        <View style={styles.actions}>
          {!isLoading && (
            <React.Fragment>
              <TouchableOpacity onPress={handleCopy} style={styles.iconButton}>
                <Ionicons name="copy-outline" size={14} />
              </TouchableOpacity>
              <TouchableOpacity onPress={handleShare} style={styles.iconButton}>
                <Ionicons name="share-social-outline" size={14} />
              </TouchableOpacity>
            </React.Fragment>
          )}
        </View>
      </View>

      {/* Message text */}
      <View style={styles.messageContainer}>
        {isLoading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="small" color="#666" />
            <Text style={styles.loadingText}>{text}</Text>
          </View>
        ) : (
          <Text style={styles.text}>{text}</Text>
        )}
      </View>

      {/* Sources */}
      {sources && sources.length > 0 && !isLoading && (
        <View style={styles.sourcesContainer}>
          <Text style={styles.sourcesTitle}>Sources:</Text>
          {sources.map((source, index) => (
            <Text key={index} style={styles.sourceItem}>• {source}</Text>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#F2F2F2",
    width: "100%",
    paddingHorizontal: 40,
    paddingVertical: 30,
    marginVertical: 6,
  },
  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  shadow: {
    backgroundColor: "black",
  },
  avatar: {
    width: 35,
    height: 35,
    borderRadius: 12,
  },
  actions: {
    flexDirection: "row",
    marginRight: 12,
  },
  iconButton: {
    marginLeft: 12,
  },
  messageContainer: {
    marginTop: 18,
  },
  text: {
    fontSize: 14,
    fontFamily: "Urbanist_400Regular",
    color: "#000",
    lineHeight: 19,
  },
  loadingContainer: {
    flexDirection: "row",
    alignItems: "center",
  },
  loadingText: {
    fontSize: 14,
    fontFamily: "Urbanist_400Regular",
    color: "#666",
    marginLeft: 10,
    fontStyle: "italic",
  },
  sourcesContainer: {
    marginTop: 15,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: "#E0E0E0",
  },
  sourcesTitle: {
    fontSize: 12,
    fontFamily: "Urbanist_600SemiBold",
    color: "#007AFF",
    marginBottom: 5,
  },
  sourceItem: {
    fontSize: 11,
    fontFamily: "Urbanist_400Regular",
    color: "#666",
    marginBottom: 2,
  },
});
