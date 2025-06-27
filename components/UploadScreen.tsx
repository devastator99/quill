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

// Replace with your actual backend URL
const BACKEND_URL = 'http://localhost:8000'; // Update this to your backend URL

interface ChunkResponse {
  chunk_id: string;
  text_snippet: string;
  summary: string;
  socratic_questions: string[];
}

const UploadScreen = () => {
  const [files, setFiles] = useState<DocumentPickerResponse[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState<boolean | null>(null);
  const [processedChunks, setProcessedChunks] = useState<ChunkResponse[]>([]);

  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.pick({
        type: DocumentPicker.types.pdf,
        allowMultiSelection: true,
      });

      setFiles(result);
      setUploadSuccess(null); // reset state on new selection
      setProcessedChunks([]); // reset processed chunks
    } catch (err) {
      if (DocumentPicker.isCancel(err)) {
        console.log('User cancelled picker');
      } else {
        Alert.alert('Error', 'Failed to pick documents.');
      }
    }
  };

  const removeFile = (uri: string) => {
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
    setProcessedChunks([]);

    try {
      // Process each file individually
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        
        formData.append('file', {
          uri: file.uri,
          type: file.type || 'application/pdf',
          name: file.name || `file${i}.pdf`,
        } as any);

        const response = await axios.post(`${BACKEND_URL}/upload_pdf/`, formData, {
          headers: { 
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const progress = (progressEvent.loaded / (progressEvent.total || 1)) * ((i + 1) / files.length);
            setUploadProgress(progress);
          },
        });

        // Add the processed chunks to our state
        const chunks: ChunkResponse[] = response.data;
        setProcessedChunks(prev => [...prev, ...chunks]);
      }

      setUploading(false);
      setUploadSuccess(true);
      Alert.alert(
        'Success!', 
        `Successfully processed ${files.length} PDF(s) and generated ${processedChunks.length} chunks with Socratic questions.`
      );
    } catch (err: any) {
      console.error('Upload error:', err);
      setUploading(false);
      setUploadSuccess(false);
      
      const errorMessage = err.response?.data?.detail || 'Failed to upload and process PDF';
      Alert.alert('Upload Error', errorMessage);
    }
  };

  const renderFileItem = ({ item }: { item: DocumentPickerResponse }) => (
    <View style={styles.fileItem}>
      <View style={{ flex: 1 }}>
        <Text style={styles.fileName}>{item.name}</Text>
        <Text style={styles.fileSize}>{((item.size || 0) / 1024).toFixed(2)} KB</Text>
      </View>
      <TouchableOpacity onPress={() => removeFile(item.uri)}>
        <Text style={styles.removeText}>Remove</Text>
      </TouchableOpacity>
    </View>
  );

  const renderChunkItem = ({ item }: { item: ChunkResponse }) => (
    <View style={styles.chunkItem}>
      <Text style={styles.chunkSummary}>{item.summary}</Text>
      <Text style={styles.chunkSnippet}>{item.text_snippet}</Text>
      <View style={styles.questionsContainer}>
        <Text style={styles.questionsTitle}>Socratic Questions:</Text>
        {item.socratic_questions.map((question, index) => (
          <Text key={index} style={styles.question}>• {question}</Text>
        ))}
      </View>
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
      <Text style={styles.title}>PDF Socratic Processor</Text>

      <Button title="Select PDF Files" onPress={pickDocument} />

      {files.length > 0 && (
        <View>
          <Text style={styles.sectionTitle}>Selected Files:</Text>
          <FlatList
            data={files}
            keyExtractor={(item) => item.uri}
            renderItem={renderFileItem}
            style={styles.fileList}
          />
        </View>
      )}

      {uploading && (
        <View style={styles.progressContainer}>
          <ActivityIndicator size="large" color="#007BFF" />
          <Text style={styles.progressText}>
            Processing: {(uploadProgress * 100).toFixed(0)}%
          </Text>
          <Text style={styles.progressSubtext}>
            Extracting text, generating embeddings, and creating Socratic questions...
          </Text>
        </View>
      )}

      {!uploading && files.length > 0 && (
        <Button title="Process PDFs" onPress={uploadFiles} color="#28a745" />
      )}

      {renderAnimation()}

      {processedChunks.length > 0 && (
        <View style={styles.resultsContainer}>
          <Text style={styles.sectionTitle}>Processed Chunks ({processedChunks.length}):</Text>
          <FlatList
            data={processedChunks}
            keyExtractor={(item) => item.chunk_id}
            renderItem={renderChunkItem}
            style={styles.chunksList}
            showsVerticalScrollIndicator={false}
          />
        </View>
      )}
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
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginTop: 20,
    marginBottom: 10,
    color: '#333',
  },
  fileList: {
    marginVertical: 10,
    maxHeight: 150,
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
    fontWeight: '600',
  },
  progressSubtext: {
    marginTop: 5,
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
  lottie: {
    width: 100,
    height: 100,
    alignSelf: 'center',
    marginTop: 20,
  },
  resultsContainer: {
    flex: 1,
    marginTop: 20,
  },
  chunksList: {
    flex: 1,
  },
  chunkItem: {
    backgroundColor: '#f8f9fa',
    padding: 15,
    marginBottom: 10,
    borderRadius: 10,
    borderLeftWidth: 4,
    borderLeftColor: '#007BFF',
  },
  chunkSummary: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  chunkSnippet: {
    fontSize: 14,
    color: '#666',
    marginBottom: 10,
    fontStyle: 'italic',
  },
  questionsContainer: {
    marginTop: 10,
  },
  questionsTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007BFF',
    marginBottom: 5,
  },
  question: {
    fontSize: 14,
    color: '#333',
    marginBottom: 3,
    paddingLeft: 10,
  },
});

export default UploadScreen;
