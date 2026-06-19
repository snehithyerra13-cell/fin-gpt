import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import App from "./App";
import AuthScreen from "./AuthScreen";
import ResultScreen from "./ResultScreen";

const Stack = createNativeStackNavigator();

export default function Navigation() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Auth"
        screenOptions={{
          headerStyle: { backgroundColor: "#121212" },
          headerTintColor: "#fff",
          headerTitleStyle: { fontWeight: "bold" },
        }}
      >
        <Stack.Screen
          name="Auth"
          component={AuthScreen}
          options={{ title: "Login / Signup" }}
        />
        <Stack.Screen
          name="Home"
          component={App}
          options={{ title: "Home" }}
        />
        <Stack.Screen
          name="Result"
          component={ResultScreen}
          options={{ title: "Results" }}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
