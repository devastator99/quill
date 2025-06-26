// UploadPDFScreen.js

import React, { useState } from 'react';
import {
  View,
  Text,
  Button,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import DocumentPicker, { DocumentPickerResponse } from 'react-native-document-picker';
import LottieView from 'lottie-react-native';
import axios from 'axios';

const UploadScreen = () => {
  const [files, setFiles] = useState<DocumentPickerResponse[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState<boolean | null>(null);

  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.pick({
        type: DocumentPicker.types.pdf,
        allowMultiSelection: true,
      });

      setFiles(result);
      setUploadSuccess(null); // reset state on new selection
    } catch (err) {
      if (DocumentPicker.isCancel(err)) {
        console.log('User cancelled picker');
      } else {
        Alert.alert('Error', 'Failed to pick documents.');
      }
    }
  };

  const removeFile = (uri:any) => {
    setFiles(files.filter(file => file.uri !== uri));
  };

  const uploadFiles = async () => {
    if (files.length === 0) {
      Alert.alert('No File', 'Please select at least one PDF.');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadSuccess(null);

    const formData = new FormData();
    files.forEach((file, index) => {
      formData.append('file' + index, {
        uri: file.uri,
        type: file.type || 'application/pdf',
        name: file.name || `file${index}.pdf`,
      } as any);
    });

    try {
      await axios.post('https://example.com/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const progress = progressEvent.loaded / (progressEvent.total || 1);
          setUploadProgress(progress);
        },
      });

      setUploading(false);
      setUploadSuccess(true);
    } catch (err) {
      console.log(err);
      setUploading(false);
      setUploadSuccess(false);
    }
  };

  const renderFileItem = (item:any) => (
    <View style={styles.fileItem}>
      <View style={{ flex: 1 }}>
        <Text style={styles.fileName}>{item.name}</Text>
        <Text style={styles.fileSize}>{(item.size / (1024)).toFixed(2)} KB</Text>
      </View>
      <TouchableOpacity onPress={() => removeFile(item.uri)}>
        <Text style={styles.removeText}>Remove</Text>
      </TouchableOpacity>
    </View>
  );

  const renderAnimation = () => {
    if (uploadSuccess === true) {
      return <LottieView source={require('./animations/success.json')} autoPlay loop={false} style={styles.lottie} />;
    } else if (uploadSuccess === false) {
      return <LottieView source={require('./animations/failure.json')} autoPlay loop={false} style={styles.lottie} />;
    }
    return null;
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>PDF Uploader</Text>

      <Button title="Select PDF Files" onPress={pickDocument} />

      <FlatList
        data={files}
        keyExtractor={(item) => item.uri}
        renderItem={renderFileItem}
        style={styles.fileList}
      />

      {uploading && (
        <View style={styles.progressContainer}>
          <ActivityIndicator size="large" color="#007BFF" />
          <Text style={styles.progressText}>
            Uploading: {(uploadProgress * 100).toFixed(0)}%
          </Text>
        </View>
      )}

      {!uploading && files.length > 0 && (
        <Button title="Upload" onPress={uploadFiles} color="#28a745" />
      )}

      {renderAnimation()}
    </View>
  );
};


const styles = StyleSheet.create({
    container: {
      flex: 1,
      padding: 20,
      backgroundColor: '#fefefe',
    },
    title: {
      fontSize: 24,
      fontWeight: '600',
      marginBottom: 15,
      textAlign: 'center',
    },
    fileList: {
      marginVertical: 20,
    },
    fileItem: {
      flexDirection: 'row',
      padding: 10,
      backgroundColor: '#f3f3f3',
      marginBottom: 8,
      borderRadius: 8,
      alignItems: 'center',
    },
    fileName: {
      fontSize: 16,
      fontWeight: '500',
    },
    fileSize: {
      fontSize: 12,
      color: '#666',
    },
    removeText: {
      color: 'red',
      fontWeight: 'bold',
    },
    progressContainer: {
      alignItems: 'center',
      marginVertical: 20,
    },
    progressText: {
      marginTop: 10,
      fontSize: 16,
    },
    lottie: {
      width: 100,
      height: 100,
      alignSelf: 'center',
      marginTop: 20,
    },
  });
  

export default UploadScreen;
