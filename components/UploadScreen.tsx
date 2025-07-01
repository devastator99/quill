// UploadPDFScreen.js

import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  Button,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from "react-native";
import DocumentPicker, {
  DocumentPickerResponse,
} from "react-native-document-picker";
import LottieView from "lottie-react-native";
import axios from "axios";

// Replace with your actual backend URL
const BACKEND_URL = "http://localhost:8000"; // Update this to your backend URL

interface ChunkResponse {
  chunk_id: string;
  text_snippet: string;
  summary: string;
  socratic_questions: string[];
  filename: string;
  page_number: number;
  confidence: number;
}

interface UploadResponse {
  upload_id: string;
  status: string;
  message: string;
  total_chunks: number;
  estimated_time: string;
  preview_chunks: ChunkResponse[];
  file_type: string;
  supported_operations: string[];
}

interface ProcessingStatus {
  upload_id: string;
  status: "PROCESSING" | "COMPLETED" | "FAILED";
  progress: number;
  message: string;
  processing_stage: string;
}

const UploadScreen = () => {
  const [files, setFiles] = useState<DocumentPickerResponse[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState<boolean | null>(null);
  const [processedChunks, setProcessedChunks] = useState<ChunkResponse[]>([]);
  const [activeUploads, setActiveUploads] = useState<UploadResponse[]>([]);
  const [processingStatuses, setProcessingStatuses] = useState<Map<string, ProcessingStatus>>(new Map());

  // Poll for processing status updates
  useEffect(() => {
    if (activeUploads.length === 0) return;

    const pollInterval = setInterval(async () => {
      try {
        for (const upload of activeUploads) {
          if (upload.status === "PROCESSING") {
            const statusResponse = await axios.get(`${BACKEND_URL}/upload_status/${upload.upload_id}`);
            const status: ProcessingStatus = statusResponse.data;
            
            setProcessingStatuses(prev => new Map(prev.set(upload.upload_id, status)));
            
            if (status.status === "COMPLETED") {
              // Fetch final chunks
              const chunksResponse = await axios.get(`${BACKEND_URL}/final_chunks/${upload.upload_id}`);
              const finalChunks: ChunkResponse[] = chunksResponse.data.chunks;
              setProcessedChunks(prev => [...prev, ...finalChunks]);
              
              // Remove from active uploads
              setActiveUploads(prev => prev.filter(u => u.upload_id !== upload.upload_id));
              setUploadSuccess(true);
            } else if (status.status === "FAILED") {
              setActiveUploads(prev => prev.filter(u => u.upload_id !== upload.upload_id));
              Alert.alert("Processing Failed", status.message);
            }
          }
        }
      } catch (error) {
        console.error("Error polling status:", error);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [activeUploads]);

  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.pick({
        type: [
          DocumentPicker.types.pdf,
          DocumentPicker.types.csv,
          DocumentPicker.types.xlsx,
          "text/markdown",
        ],
        allowMultiSelection: true,
      });

      setFiles(result);
      setUploadSuccess(null); // reset state on new selection
      setProcessedChunks([]); // reset processed chunks
      setActiveUploads([]); // reset active uploads
      setProcessingStatuses(new Map());
    } catch (err) {
      if (DocumentPicker.isCancel(err)) {
        console.log("User cancelled picker");
      } else {
        Alert.alert("Error", "Failed to pick documents.");
      }
    }
  };

  const removeFile = (uri: string) => {
    setFiles(files.filter((file) => file.uri !== uri));
  };

  const uploadFiles = async () => {
    if (files.length === 0) {
      Alert.alert("No File", "Please select at least one file.");
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadSuccess(null);
    setProcessedChunks([]);
    setActiveUploads([]);

    try {
      const newUploads: UploadResponse[] = [];
      
      // Process each file individually
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();

        formData.append("file", {
          uri: file.uri,
          type: file.type || "application/octet-stream", // Default type
          name: file.name || `file${i}.pdf`,
        } as any);

        const response = await axios.post(
          `${BACKEND_URL}/upload_doc/`,
          formData,
          {
            headers: {
              "Content-Type": "multipart/form-data",
            },
            onUploadProgress: (progressEvent) => {
              const progress =
                (progressEvent.loaded / (progressEvent.total || 1)) *
                ((i + 1) / files.length);
              setUploadProgress(progress);
            },
          }
        );

        // Store the upload response for background processing tracking
        const uploadResponse: UploadResponse = response.data;
        newUploads.push(uploadResponse);
        
        // Add preview chunks immediately
        setProcessedChunks((prev) => [...prev, ...uploadResponse.preview_chunks]);
      }

      setActiveUploads(newUploads);
      setUploading(false);
      
      const totalChunks = newUploads.reduce((sum, upload) => sum + upload.total_chunks, 0);
      Alert.alert(
        "Upload Started!",
        `Successfully initiated processing of ${files.length} file(s). Background processing will generate ${totalChunks} total chunks with Socratic questions. You can track progress below.`
      );
    } catch (err: any) {
      console.error("Upload error:", err);
      setUploading(false);
      setUploadSuccess(false);

      const errorMessage =
        err.response?.data?.detail || "Failed to upload and process file";
      Alert.alert("Upload Error", errorMessage);
    }
  };

  const getFileTypeDisplay = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf':
        return '📄 PDF';
      case 'csv':
        return '📊 CSV';
      case 'xlsx':
      case 'xls':
        return '📈 Excel';
      case 'md':
      case 'markdown':
        return '📝 Markdown';
      default:
        return '📎 File';
    }
  };

  const renderFileItem = ({ item }: { item: DocumentPickerResponse }) => (
    <View style={styles.fileItem}>
      <View style={{ flex: 1 }}>
        <Text style={styles.fileName}>{item.name}</Text>
        <View style={styles.fileInfoRow}>
          <Text style={styles.fileType}>{getFileTypeDisplay(item.name || "")}</Text>
          <Text style={styles.fileSize}>
            {((item.size || 0) / 1024).toFixed(2)} KB
          </Text>
        </View>
      </View>
      <TouchableOpacity onPress={() => removeFile(item.uri)}>
        <Text style={styles.removeText}>Remove</Text>
      </TouchableOpacity>
    </View>
  );

  const renderChunkItem = ({ item }: { item: ChunkResponse }) => (
    <View style={styles.chunkItem}>
      <View style={styles.chunkHeader}>
        <Text style={styles.chunkSummary}>{item.summary}</Text>
        <View style={styles.metadataRow}>
          <Text style={styles.filename}>{item.filename}</Text>
          <Text style={styles.pageNumber}>Page {item.page_number}</Text>
          <Text style={[
            styles.confidence, 
            { color: item.confidence > 0.8 ? '#28a745' : item.confidence > 0.5 ? '#ffc107' : '#dc3545' }
          ]}>
            {(item.confidence * 100).toFixed(0)}% confidence
          </Text>
        </View>
      </View>
      <Text style={styles.chunkSnippet}>{item.text_snippet}</Text>
      <View style={styles.questionsContainer}>
        <Text style={styles.questionsTitle}>🤔 Socratic Questions:</Text>
        {item.socratic_questions.map((question, index) => (
          <Text key={index} style={styles.question}>
            • {question}
          </Text>
        ))}
      </View>
    </View>
  );

  const renderProcessingStatus = ({ item }: { item: UploadResponse }) => {
    const status = processingStatuses.get(item.upload_id);
    
    return (
      <View style={styles.processingItem}>
        <View style={styles.processingHeader}>
          <Text style={styles.processingTitle}>📄 {item.file_type} Processing</Text>
          <Text style={styles.estimatedTime}>⏱️ {item.estimated_time}</Text>
        </View>
        
        <Text style={styles.processingMessage}>{item.message}</Text>
        
        {status && (
          <View style={styles.statusContainer}>
            <View style={styles.progressRow}>
              <Text style={styles.statusText}>{status.processing_stage}</Text>
              <Text style={styles.progressText}>{status.progress}%</Text>
            </View>
            <View style={styles.progressBar}>
              <View 
                style={[styles.progressFill, { width: `${status.progress}%` }]} 
              />
            </View>
            <Text style={styles.statusMessage}>{status.message}</Text>
          </View>
        )}
        
        <View style={styles.featuresContainer}>
          <Text style={styles.featuresTitle}>✨ Features:</Text>
          <View style={styles.featuresGrid}>
            {item.supported_operations.map((feature, index) => (
              <Text key={index} style={styles.featureTag}>
                {feature}
              </Text>
            ))}
          </View>
        </View>
        
        <Text style={styles.chunkCount}>
          📊 {item.total_chunks} chunks • {item.preview_chunks.length} preview ready
        </Text>
      </View>
    );
  };

  const renderAnimation = () => {
    if (uploadSuccess === true) {
      return (
        <LottieView
          source={require("./animations/success.json")}
          autoPlay
          loop={false}
          style={styles.lottie}
        />
      );
    } else if (uploadSuccess === false) {
      return (
        <LottieView
          source={require("./animations/failure.json")}
          autoPlay
          loop={false}
          style={styles.lottie}
        />
      );
    }
    return null;
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Document Socratic Processor</Text>

      <Button title="Select Files (PDF, CSV, Excel, Markdown)" onPress={pickDocument} />

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
            Extracting text, generating embeddings, and creating Socratic
            questions...
          </Text>
        </View>
      )}

      {!uploading && files.length > 0 && (
        <Button title="Process Documents" onPress={uploadFiles} color="#28a745" />
      )}

      {renderAnimation()}

      {activeUploads.length > 0 && (
        <View style={styles.resultsContainer}>
          <Text style={styles.sectionTitle}>
            🔄 Processing Status ({activeUploads.length} files):
          </Text>
          <FlatList
            data={activeUploads}
            keyExtractor={(item) => item.upload_id}
            renderItem={renderProcessingStatus}
            style={styles.processingList}
            showsVerticalScrollIndicator={false}
          />
        </View>
      )}

      {processedChunks.length > 0 && (
        <View style={styles.resultsContainer}>
          <Text style={styles.sectionTitle}>
            📋 Processed Chunks ({processedChunks.length}):
          </Text>
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
    backgroundColor: "#fefefe",
  },
  title: {
    fontSize: 24,
    fontWeight: "600",
    marginBottom: 15,
    textAlign: "center",
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    marginTop: 20,
    marginBottom: 10,
    color: "#333",
  },
  fileList: {
    marginVertical: 10,
    maxHeight: 150,
  },
  fileItem: {
    flexDirection: "row",
    padding: 10,
    backgroundColor: "#f3f3f3",
    marginBottom: 8,
    borderRadius: 8,
    alignItems: "center",
  },
  fileName: {
    fontSize: 16,
    fontWeight: "500",
  },
  fileInfoRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  fileType: {
    fontSize: 12,
    color: "#007BFF",
    fontWeight: "500",
  },
  fileSize: {
    fontSize: 12,
    color: "#666",
  },
  removeText: {
    color: "red",
    fontWeight: "bold",
  },
  progressContainer: {
    alignItems: "center",
    marginVertical: 20,
  },
  progressText: {
    marginTop: 10,
    fontSize: 16,
    fontWeight: "600",
  },
  progressSubtext: {
    marginTop: 5,
    fontSize: 12,
    color: "#666",
    textAlign: "center",
  },
  lottie: {
    width: 100,
    height: 100,
    alignSelf: "center",
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
    backgroundColor: "#f8f9fa",
    padding: 15,
    marginBottom: 10,
    borderRadius: 10,
    borderLeftWidth: 4,
    borderLeftColor: "#007BFF",
  },
  chunkHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  chunkSummary: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
  },
  metadataRow: {
    flexDirection: "row",
    alignItems: "center",
    marginLeft: 10,
  },
  filename: {
    fontSize: 12,
    color: "#666",
  },
  pageNumber: {
    fontSize: 12,
    color: "#666",
    marginLeft: 10,
  },
  confidence: {
    fontSize: 12,
    color: "#666",
  },
  chunkSnippet: {
    fontSize: 14,
    color: "#666",
    marginBottom: 10,
    fontStyle: "italic",
  },
  questionsContainer: {
    marginTop: 10,
  },
  questionsTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#007BFF",
    marginBottom: 5,
  },
  question: {
    fontSize: 14,
    color: "#333",
    marginBottom: 3,
    paddingLeft: 10,
  },
  processingItem: {
    backgroundColor: "#f8f9fa",
    padding: 15,
    marginBottom: 10,
    borderRadius: 10,
    borderLeftWidth: 4,
    borderLeftColor: "#007BFF",
  },
  processingHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  processingTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
  },
  estimatedTime: {
    fontSize: 12,
    color: "#666",
  },
  processingMessage: {
    fontSize: 14,
    color: "#666",
    marginBottom: 10,
  },
  statusContainer: {
    marginBottom: 10,
  },
  statusText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#333",
  },
  progressBar: {
    height: 10,
    backgroundColor: "#f0f0f0",
    borderRadius: 5,
    marginBottom: 5,
  },
  progressFill: {
    height: "100%",
    backgroundColor: "#007BFF",
    borderRadius: 5,
  },
  statusMessage: {
    fontSize: 14,
    color: "#666",
  },
  progressRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 5,
  },
  featuresContainer: {
    marginBottom: 10,
  },
  featuresTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#333",
    marginBottom: 5,
  },
  featuresGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  featureTag: {
    backgroundColor: "#e7f3ff",
    color: "#007BFF",
    fontSize: 12,
    fontWeight: "500",
    padding: 5,
    marginRight: 5,
    marginBottom: 5,
    borderRadius: 5,
  },
  chunkCount: {
    fontSize: 14,
    color: "#666",
  },
  processingList: {
    maxHeight: 200,
    marginBottom: 15,
  },
});

export default UploadScreen;
