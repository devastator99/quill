import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  Share,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import Clipboard from "expo-clipboard";
import { ImageSourcePropType } from "react-native";
import ShadowContainer from "./ShadowContainer";

export default function ResponseBubble({
  avatar,
  text,
}: {
  avatar: ImageSourcePropType;
  text: string;
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
          <TouchableOpacity onPress={handleCopy} style={styles.iconButton}>
            <Ionicons name="copy-outline" size={14} />
          </TouchableOpacity>
          <TouchableOpacity onPress={handleShare} style={styles.iconButton}>
            <Ionicons name="share-social-outline" size={14} />
          </TouchableOpacity>
        </View>
      </View>

      {/* Message text */}
      <Text style={styles.text}>{text}</Text>
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
  text: {
    marginTop: 18,
    fontSize: 12,
    fontFamily: "Urbanist_400Regular_Italic",
    color: "#000",
    lineHeight: 17,
  },
});
