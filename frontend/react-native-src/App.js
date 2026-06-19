import Checkbox from "expo-checkbox";
import * as DocumentPicker from "expo-document-picker";
import * as FileSystem from "expo-file-system";
import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  SafeAreaView,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import SwitchToggle from "react-native-switch-toggle";
import { API_URL } from "./config";
import styles from "./styles";

export default function App({ navigation }) {
  const [pdfFile, setPdfFile] = useState(null);
  const [summarize, setSummarize] = useState(false);
  const [classify, setClassify] = useState(false);
  const [qaPdf, setQaPdf] = useState(false);
  const [qaQuery, setQaQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(true);

  const theme = darkMode ? styles.dark : styles.light;

const handlePdfUpload = async () => {
  try {
    const res = await DocumentPicker.getDocumentAsync({
      type: "application/pdf",
      copyToCacheDirectory: true,
    });

    if (!res.canceled && res.assets?.length > 0) {
      const pickedFile = res.assets[0];
      console.log("Original picked file:", pickedFile);

      // Create a stable cache path
      const newUri = `${FileSystem.cacheDirectory}${pickedFile.name}`;
      
      // Copy the file to the cache directory to avoid losing it on reloads
      await FileSystem.copyAsync({
        from: pickedFile.uri,
        to: newUri,
      });

      // Set the file with the new stable URI
      setPdfFile({
        ...pickedFile,
        uri: newUri,
      });

      console.log("Copied file to stable URI:", newUri);
    } else {
      setPdfFile(null);
    }
  } catch (err) {
    console.error("Document Picker Error:", err);
    Alert.alert("Error", "Failed to pick a document.");
  }
};


  const handleProcess = async () => {
  if (loading) return;
  if (!pdfFile || !pdfFile.uri) {
    Alert.alert("Upload a PDF file first");
    return;
  }
  if (!summarize && !classify && !qaPdf) {
    Alert.alert("Select at least one processing option.");
    return;
  }
  if (qaPdf && !qaQuery.trim()) {
    Alert.alert("Please enter your question.");
    return;
  }

  console.log("About to read file as base64:", pdfFile.uri);
  setLoading(true);

  try {
    const base64 = await FileSystem.readAsStringAsync(pdfFile.uri, {
      encoding: FileSystem.EncodingType.Base64,
    });

    const response = await fetch(`${API_URL}/process/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: pdfFile.name,
        filedata: base64,
        summarize_checked: summarize,
        classify_checked: classify,
        qa_checked: qaPdf,
        qa_query: qaQuery,
      }),
    });

    const text = await response.text();
    console.log("Process Raw response text:", text);

    if (!response.ok) {
      let detail = "Unknown error";
      try {
        const errorJson = JSON.parse(text);
        detail = errorJson.detail || detail;
      } catch {}
      throw new Error(detail);
    }

    const data = JSON.parse(text);
    console.log("Parsed Process JSON:", data);

    if (data) {
      navigation.navigate("Result", { result: data, darkMode });
      setPdfFile(null);
    } else {
      throw new Error("Empty response data.");
    }
  } catch (error) {
    console.error("Process error:", error);
    Alert.alert("Error", `Failed: ${error.message}`);
  } finally {
    setLoading(false);
  }
};


  const handleChat = async () => {
    if (chatLoading || !chatInput.trim()) {
      return Alert.alert("Please enter your question.");
    }

    setChatLoading(true);
    try {
      const response = await fetch(`${API_URL}/general-chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: chatInput }),
      });

      const text = await response.text();
      const data = JSON.parse(text);

      if (!response.ok) throw new Error(data?.detail || "Chat failed");

      navigation.navigate("Result", {
        result: { "Chatbot Answer": data.answer },
        darkMode,
      });
      setChatInput("");
    } catch (err) {
      console.error("Chat Error:", err);
      Alert.alert("Error", `Chat failed: ${err.message}`);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <SafeAreaView style={theme.container}>
      <ScrollView>
        {/* Header & Dark Mode Toggle */}
        <View style={theme.headerRow}>
          <Text style={theme.title}>💼 GeniFi</Text>
          <View style={{ flexDirection: "row", alignItems: "center" }}>
            <Text style={{ fontSize: 18, marginRight: 8 }}>
              {darkMode ? "🌙" : "☀️"}
            </Text>
            <SwitchToggle
              switchOn={darkMode}
              onPress={() => setDarkMode(!darkMode)}
              containerStyle={{
                width: 70,
                height: 35,
                borderRadius: 25,
                padding: 4,
              }}
              backgroundColorOn="#B983FF"
              backgroundColorOff="#ccc"
              circleStyle={{
                width: 27,
                height: 27,
                borderRadius: 15,
                backgroundColor: "white",
              }}
              renderInsideCircle={() => (
                <Text style={{ fontSize: 14 }}>
                  {darkMode ? "🌙" : "☀️"}
                </Text>
              )}
            />
          </View>
        </View>

        {/* PDF Upload Button */}
        <TouchableOpacity style={theme.uploadBtn} onPress={handlePdfUpload}>
          <Text style={theme.uploadText}>
            {pdfFile ? `📑 ${pdfFile.name}` : "📤 Upload PDF"}
          </Text>
        </TouchableOpacity>

        {/* Processing Options */}
        <View style={theme.checkboxContainer}>
          {[{ label: "Summarize", value: summarize, setter: setSummarize },
            { label: "Classify", value: classify, setter: setClassify },
            { label: "Q&A from PDF", value: qaPdf, setter: setQaPdf }].map(opt => (
            <View key={opt.label} style={theme.checkboxRow}>
              <Checkbox
                value={opt.value}
                onValueChange={opt.setter}
                color={opt.value ? "#B983FF" : undefined}
              />
              <Text style={theme.label}>{opt.label}</Text>
            </View>
          ))}

          {qaPdf && (
            <TextInput
              style={theme.input}
              placeholder="Enter your question about the PDF"
              placeholderTextColor="#aaa"
              value={qaQuery}
              onChangeText={setQaQuery}
            />
          )}
        </View>

        {/* Process Button */}
        <TouchableOpacity
          style={[theme.processBtn, loading && { opacity: 0.6 }]}
          onPress={handleProcess}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={theme.processText}>▶ Process</Text>
          )}
        </TouchableOpacity>

        <View style={theme.divider} />

        {/* General Chat Section */}
        <Text style={theme.chatTitle}>🤖 Finance Chatbot</Text>
        <TextInput
          style={theme.input}
          placeholder="Ask about loans, investments..."
          placeholderTextColor="#aaa"
          value={chatInput}
          onChangeText={setChatInput}
        />
        <TouchableOpacity
          style={[theme.chatBtn, chatLoading && { opacity: 0.6 }]}
          onPress={handleChat}
          disabled={chatLoading}
        >
          {chatLoading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={theme.chatText}>Ask</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}
