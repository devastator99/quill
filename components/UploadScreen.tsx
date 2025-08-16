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
  Modal,
  ScrollView,
  Dimensions,
} from "react-native";
import DocumentPicker, {
  DocumentPickerResponse,
} from "@react-native-documents/picker";
import LottieView from "lottie-react-native";
import axios from "axios";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");

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
  
  // Modal states
  const [statusModalVisible, setStatusModalVisible] = useState(false);
  const [chunksModalVisible, setChunksModalVisible] = useState(false);
  const [selectedChunk, setSelectedChunk] = useState<ChunkResponse | null>(null);
  const [chunkDetailModalVisible, setChunkDetailModalVisible] = useState(false);

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

  const openChunkDetail = (chunk: ChunkResponse) => {
    setSelectedChunk(chunk);
    setChunkDetailModalVisible(true);
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

  const renderStatusModal = () => (
    <Modal
      animationType="slide"
      transparent={true}
      visible={statusModalVisible}
      onRequestClose={() => setStatusModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>🔄 Processing Status</Text>
            <TouchableOpacity 
              onPress={() => setStatusModalVisible(false)}
              style={styles.closeButton}
            >
              <Ionicons name="close" size={24} color="#666" />
            </TouchableOpacity>
          </View>
          
          <ScrollView style={styles.modalContent} showsVerticalScrollIndicator={false}>
            {activeUploads.map((upload, index) => {
              const status = processingStatuses.get(upload.upload_id);
              return (
                <View key={upload.upload_id} style={styles.statusCard}>
                  <LinearGradient
                    colors={['#f8f9fa', '#e9ecef']}
                    style={styles.statusCardGradient}
                  >
                    <View style={styles.statusHeader}>
                      <Text style={styles.statusTitle}>
                        {getFileTypeDisplay(upload.file_type)} Processing
                      </Text>
                      <Text style={styles.estimatedTime}>⏱️ {upload.estimated_time}</Text>
                    </View>
                    
                    <Text style={styles.statusMessage}>{upload.message}</Text>
                    
                    {status && (
                      <View style={styles.progressSection}>
                        <View style={styles.progressHeader}>
                          <Text style={styles.progressStage}>{status.processing_stage}</Text>
                          <Text style={styles.progressPercentage}>{status.progress}%</Text>
                        </View>
                        <View style={styles.progressBarContainer}>
                          <View 
                            style={[styles.progressBar, { width: `${status.progress}%` }]} 
                          />
                        </View>
                        <Text style={styles.progressMessage}>{status.message}</Text>
                      </View>
                    )}
                    
                    <View style={styles.featuresSection}>
                      <Text style={styles.featuresTitle}>✨ Features:</Text>
                      <View style={styles.featuresGrid}>
                        {upload.supported_operations.map((feature, idx) => (
                          <View key={idx} style={styles.featureChip}>
                            <Text style={styles.featureText}>{feature}</Text>
                          </View>
                        ))}
                      </View>
                    </View>
                    
                    <Text style={styles.chunkInfo}>
                      📊 {upload.total_chunks} chunks • {upload.preview_chunks.length} preview ready
                    </Text>
                  </LinearGradient>
                </View>
              );
            })}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );

  const renderChunksModal = () => (
    <Modal
      animationType="slide"
      transparent={true}
      visible={chunksModalVisible}
      onRequestClose={() => setChunksModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>📋 Processed Chunks ({processedChunks.length})</Text>
            <TouchableOpacity 
              onPress={() => setChunksModalVisible(false)}
              style={styles.closeButton}
            >
              <Ionicons name="close" size={24} color="#666" />
            </TouchableOpacity>
          </View>
          
          <FlatList
            data={processedChunks}
            keyExtractor={(item) => item.chunk_id}
            renderItem={({ item }) => (
              <TouchableOpacity 
                style={styles.chunkCard}
                onPress={() => openChunkDetail(item)}
                activeOpacity={0.7}
              >
                <LinearGradient
                  colors={['#ffffff', '#f8f9fa']}
                  style={styles.chunkCardGradient}
                >
                  <View style={styles.chunkHeader}>
                    <Text style={styles.chunkSummary} numberOfLines={2}>
                      {item.summary}
                    </Text>
                    <Ionicons name="chevron-forward" size={16} color="#666" />
                  </View>
                  
                  <View style={styles.chunkMetadata}>
                    <Text style={styles.chunkFilename}>{item.filename}</Text>
                    <Text style={styles.chunkPage}>Page {item.page_number}</Text>
                    <View style={[
                      styles.confidenceBadge,
                      { backgroundColor: item.confidence > 0.8 ? '#d4edda' : item.confidence > 0.5 ? '#fff3cd' : '#f8d7da' }
                    ]}>
                      <Text style={[
                        styles.confidenceText,
                        { color: item.confidence > 0.8 ? '#155724' : item.confidence > 0.5 ? '#856404' : '#721c24' }
                      ]}>
                        {(item.confidence * 100).toFixed(0)}%
                      </Text>
                    </View>
                  </View>
                  
                  <Text style={styles.chunkSnippet} numberOfLines={3}>
                    {item.text_snippet}
                  </Text>
                  
                  <Text style={styles.questionsPreview}>
                    🤔 {item.socratic_questions.length} Socratic questions
                  </Text>
                </LinearGradient>
              </TouchableOpacity>
            )}
            style={styles.modalContent}
            showsVerticalScrollIndicator={false}
          />
        </View>
      </View>
    </Modal>
  );

  const renderChunkDetailModal = () => (
    <Modal
      animationType="slide"
      transparent={true}
      visible={chunkDetailModalVisible}
      onRequestClose={() => setChunkDetailModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>📄 Chunk Details</Text>
            <TouchableOpacity 
              onPress={() => setChunkDetailModalVisible(false)}
              style={styles.closeButton}
            >
              <Ionicons name="close" size={24} color="#666" />
            </TouchableOpacity>
          </View>
          
          {selectedChunk && (
            <ScrollView style={styles.modalContent} showsVerticalScrollIndicator={false}>
              <View style={styles.detailCard}>
                <Text style={styles.detailTitle}>{selectedChunk.summary}</Text>
                
                <View style={styles.detailMetadata}>
                  <View style={styles.metadataItem}>
                    <Text style={styles.metadataLabel}>File:</Text>
                    <Text style={styles.metadataValue}>{selectedChunk.filename}</Text>
                  </View>
                  <View style={styles.metadataItem}>
                    <Text style={styles.metadataLabel}>Page:</Text>
                    <Text style={styles.metadataValue}>{selectedChunk.page_number}</Text>
                  </View>
                  <View style={styles.metadataItem}>
                    <Text style={styles.metadataLabel}>Confidence:</Text>
                    <Text style={[
                      styles.metadataValue,
                      { color: selectedChunk.confidence > 0.8 ? '#28a745' : selectedChunk.confidence > 0.5 ? '#ffc107' : '#dc3545' }
                    ]}>
                      {(selectedChunk.confidence * 100).toFixed(0)}%
                    </Text>
                  </View>
                </View>
                
                <View style={styles.contentSection}>
                  <Text style={styles.detailSectionTitle}>📝 Content</Text>
                  <Text style={styles.contentText}>{selectedChunk.text_snippet}</Text>
                </View>
                
                <View style={styles.questionsSection}>
                  <Text style={styles.detailSectionTitle}>🤔 Socratic Questions</Text>
                  {selectedChunk.socratic_questions.map((question, index) => (
                    <View key={index} style={styles.questionItem}>
                      <Text style={styles.questionNumber}>{index + 1}.</Text>
                      <Text style={styles.questionText}>{question}</Text>
                    </View>
                  ))}
                </View>
              </View>
            </ScrollView>
          )}
        </View>
      </View>
    </Modal>
  );

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

      {/* Status and Chunks Action Buttons */}
      <View style={styles.actionButtonsContainer}>
        {activeUploads.length > 0 && (
          <TouchableOpacity 
            style={styles.actionButton}
            onPress={() => setStatusModalVisible(true)}
          >
            <LinearGradient
              colors={['#007BFF', '#0056b3']}
              style={styles.actionButtonGradient}
            >
              <Ionicons name="analytics" size={20} color="white" />
              <Text style={styles.actionButtonText}>
                View Status ({activeUploads.length})
              </Text>
            </LinearGradient>
          </TouchableOpacity>
        )}

        {processedChunks.length > 0 && (
          <TouchableOpacity 
            style={styles.actionButton}
            onPress={() => setChunksModalVisible(true)}
          >
            <LinearGradient
              colors={['#28a745', '#1e7e34']}
              style={styles.actionButtonGradient}
            >
              <Ionicons name="library" size={20} color="white" />
              <Text style={styles.actionButtonText}>
                View Chunks ({processedChunks.length})
              </Text>
            </LinearGradient>
          </TouchableOpacity>
        )}
      </View>

      {/* Modals */}
      {renderStatusModal()}
      {renderChunksModal()}
      {renderChunkDetailModal()}
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
  actionButtonsContainer: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginTop: 20,
    paddingHorizontal: 10,
  },
  actionButton: {
    flex: 1,
    marginHorizontal: 5,
    borderRadius: 12,
    overflow: "hidden",
    elevation: 3,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
  },
  actionButtonGradient: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  actionButtonText: {
    color: "white",
    fontSize: 14,
    fontWeight: "600",
    marginLeft: 8,
  },
  
  // Modal Styles
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    justifyContent: "center",
    alignItems: "center",
  },
  modalContainer: {
    backgroundColor: "white",
    borderRadius: 20,
    width: SCREEN_WIDTH * 0.9,
    maxHeight: SCREEN_HEIGHT * 0.8,
    elevation: 5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: "#e9ecef",
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#333",
  },
  closeButton: {
    padding: 5,
  },
  modalContent: {
    flex: 1,
    paddingHorizontal: 20,
  },
  
  // Status Modal Styles
  statusCard: {
    marginVertical: 8,
    borderRadius: 12,
    overflow: "hidden",
    elevation: 2,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  statusCardGradient: {
    padding: 15,
  },
  statusHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  statusTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
  },
  estimatedTime: {
    fontSize: 12,
    color: "#666",
  },
  statusMessage: {
    fontSize: 14,
    color: "#666",
    marginBottom: 12,
  },
  progressSection: {
    marginBottom: 12,
  },
  progressHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  progressStage: {
    fontSize: 14,
    fontWeight: "600",
    color: "#333",
  },
  progressPercentage: {
    fontSize: 14,
    fontWeight: "600",
    color: "#007BFF",
  },
  progressBarContainer: {
    height: 8,
    backgroundColor: "#e9ecef",
    borderRadius: 4,
    marginBottom: 8,
  },
  progressBar: {
    height: "100%",
    backgroundColor: "#007BFF",
    borderRadius: 4,
  },
  progressMessage: {
    fontSize: 12,
    color: "#666",
  },
  featuresSection: {
    marginBottom: 12,
  },
  featuresTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#333",
    marginBottom: 8,
  },
  featuresGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  featureChip: {
    backgroundColor: "#e7f3ff",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 6,
    marginBottom: 6,
  },
  featureText: {
    fontSize: 12,
    color: "#007BFF",
    fontWeight: "500",
  },
  chunkInfo: {
    fontSize: 12,
    color: "#666",
    fontStyle: "italic",
  },
  
  // Chunks Modal Styles
  chunkCard: {
    marginVertical: 6,
    borderRadius: 12,
    overflow: "hidden",
    elevation: 2,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
  },
  chunkCardGradient: {
    padding: 15,
  },
  chunkHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  chunkSummary: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
    flex: 1,
  },
  chunkMetadata: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  chunkFilename: {
    fontSize: 12,
    color: "#666",
    marginRight: 12,
  },
  chunkPage: {
    fontSize: 12,
    color: "#666",
    marginRight: 12,
  },
  confidenceBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
  },
  confidenceText: {
    fontSize: 10,
    fontWeight: "600",
  },
  chunkSnippet: {
    fontSize: 14,
    color: "#666",
    marginBottom: 8,
    lineHeight: 20,
  },
  questionsPreview: {
    fontSize: 12,
    color: "#007BFF",
    fontWeight: "500",
  },
  
  // Chunk Detail Modal Styles
  detailCard: {
    padding: 15,
  },
  detailTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#333",
    marginBottom: 15,
  },
  detailMetadata: {
    marginBottom: 20,
  },
  metadataItem: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  metadataLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: "#666",
    width: 80,
  },
  metadataValue: {
    fontSize: 14,
    color: "#333",
    flex: 1,
  },
  contentSection: {
    marginBottom: 20,
  },
  detailSectionTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
    marginBottom: 10,
  },
  contentText: {
    fontSize: 14,
    color: "#666",
    lineHeight: 22,
    backgroundColor: "#f8f9fa",
    padding: 12,
    borderRadius: 8,
  },
  questionsSection: {
    marginBottom: 20,
  },
  questionItem: {
    flexDirection: "row",
    marginBottom: 12,
    alignItems: "flex-start",
  },
  questionNumber: {
    fontSize: 14,
    fontWeight: "600",
    color: "#007BFF",
    marginRight: 8,
    marginTop: 2,
  },
  questionText: {
    fontSize: 14,
    color: "#333",
    flex: 1,
    lineHeight: 20,
  },
});

export default UploadScreen;
