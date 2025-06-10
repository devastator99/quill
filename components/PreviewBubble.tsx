import {
    View,
    Text,
    Image,
    TouchableOpacity,
    StyleSheet,
    Share,
    ImageSourcePropType,
  } from 'react-native';
  import { Ionicons } from '@expo/vector-icons';
  import Clipboard from 'expo-clipboard';
  import ShadowContainer from './ShadowContainer';
  
  export default function PreviewBubble({ avatar, question, onEdit }: { avatar: string, question: string, onEdit: () => void }) {
    const handleCopy = () => Clipboard.setString(question);
    const handleShare = () => {
      Share.share({ message: question });
    };
  
    return (
      <View style={styles.container}>
        <Image source={avatar as ImageSourcePropType} style={styles.avatar} />
  
        <Text style={styles.question}>{question}</Text>
  
        <View style={styles.icons}>
          <TouchableOpacity onPress={onEdit} style={styles.icon}>
            <Ionicons name="pencil" size={15} />
          </TouchableOpacity>
          <TouchableOpacity onPress={handleCopy} style={styles.icon}>
            <Ionicons name="copy-outline" size={15} />
          </TouchableOpacity>
        </View>
      </View>
    );
  }
  
  const styles = StyleSheet.create({
    container: {
      flexDirection: 'row',
      alignItems: 'center',
      marginHorizontal: 40,
      marginRight:40,
      marginVertical: 4,
      // no border or background
    },
    avatar: {
      width: 35,
      height: 35,
      borderRadius: 12,
      marginRight: 8,
      backgroundColor:'rgba(0,0,0,0)'
    },
    question: {
      flex: 1,
      fontSize: 14,
      color: '#000',
      fontFamily: 'Urbanist_400Regular',
      lineHeight: 17,
    },
    icons: {
      flexDirection: 'row',
      marginLeft: 8,
    },
    icon: {
      marginHorizontal: 4,
    },
  });
  