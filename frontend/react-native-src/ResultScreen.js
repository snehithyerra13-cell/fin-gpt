import { ScrollView, StyleSheet, Text, View } from "react-native";

export default function ResultScreen({ route }) {
  const { result, darkMode } = route.params;

  const colors = darkMode
    ? {
        background: "#121212",
        title: "#fff",
        sectionTitle: "#7B61FF",
        text: "#ccc",
      }
    : {
        background: "#fff",
        title: "#000",
        sectionTitle: "#7B61FF",
        text: "#333",
      };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
    >
      <Text style={[styles.title, { color: colors.title }]}>
        📊 Processed Results
      </Text>
      {Object.keys(result).length === 0 ? (
        <Text style={[styles.sectionContent, { color: colors.text }]}>
          No data received.
        </Text>
      ) : (
        Object.entries(result).map(([key, value]) => (
          <View key={key} style={styles.section}>
            <Text style={[styles.sectionTitle, { color: colors.sectionTitle }]}>
              {key}
            </Text>
            {typeof value === "object" && value !== null ? (
              <View style={styles.nestedContainer}>
                {Object.entries(value).map(([subKey, subValue]) => (
                  <Text
                    key={subKey}
                    style={[styles.sectionContent, { color: colors.text }]}
                  >
                    • {subKey}: {String(subValue)}
                  </Text>
                ))}
              </View>
            ) : (
              <Text style={[styles.sectionContent, { color: colors.text }]}>
                {String(value)}
              </Text>
            )}
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20 },
  title: { fontSize: 24, fontWeight: "bold", marginBottom: 20 },
  section: { marginBottom: 20 },
  sectionTitle: { fontSize: 18, fontWeight: "bold", marginBottom: 6 },
  nestedContainer: { paddingLeft: 10 },
  sectionContent: { fontSize: 16, marginBottom: 2 },
});
