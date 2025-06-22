import React, { createContext, useContext } from "react";
import { TouchableOpacity } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { AnimatedDrawer } from "@/components/AnimatedDrawer";
import { router, Stack } from "expo-router";
import { Menu } from "lucide-react-native";
import { SafeAreaView } from "react-native-safe-area-context";

type DrawerContextType = {
  toggleDrawer?: () => void;
};

const DrawerContext = createContext<DrawerContextType>({});

export const useDrawer = () => useContext(DrawerContext);

type DrawerContentProps = {
  toggleDrawer?: () => void;
};

function MenuButton({ tintColor }: { tintColor?: string }) {
  const { toggleDrawer } = useDrawer();

  return (
    <TouchableOpacity
      style={{ padding: 8, marginLeft: 8 }}
      onPress={toggleDrawer}
      activeOpacity={0.7}
    >
      <Menu size={24} color={tintColor} />
    </TouchableOpacity>
  );
}

const DrawerContent: React.FC<DrawerContentProps> = ({ toggleDrawer }) => {
  return (
    <SafeAreaView style={{ flex: 1 }}>
      <DrawerContext.Provider value={{ toggleDrawer }}>
        <Stack
          screenOptions={{
            headerShown: true,
            headerStyle: {
              backgroundColor: "rgb(241, 240, 240)",
            },
            headerTintColor: "#000000",
            headerTitleStyle: {
              fontWeight: "600",
            },
          }}
        >
          <Stack.Screen
            name="books"
            options={{
              headerShown: false, // Let books handle its own header
            }}
          />
          <Stack.Screen
            name="chat"
            options={{
              title: "Health Chat",
              headerShown: false,
              // headerLeft: ({ tintColor }) => <MenuButton tintColor={tintColor} />,
            }}
          />
          <Stack.Screen
            name="about"
            options={{
              title: "About",
              headerLeft: ({ tintColor }) => (
                <MenuButton tintColor={tintColor} />
              ),
            }}
          />
        </Stack>
      </DrawerContext.Provider>
    </SafeAreaView>
  );
};

export default function DrawerLayout() {
  const drawerItems = [
    {
      icon: "📚",
      title: "Book Catalog",
      subtitle: "Browse your library",
    },
    {
      icon: "💬",
      title: "Chat",
      subtitle: "AI conversations",
    },
    {
      icon: "ℹ️",
      title: "About",
      subtitle: "App information",
    },
  ];

  const handleItemPress = (item: any, index: number) => {
    console.log("Drawer item pressed:", item.title, "Index:", index);

    switch (index) {
      case 0:
        console.log("Navigating to books");
        router.push("/(main)/(drawer)/books/");
        break;
      case 1:
        console.log("Navigating to chat");
        router.push("/(main)/(drawer)/chat");
        break;
      case 2:
        console.log("Navigating to about");
        router.push("/(main)/(drawer)/about");
        break;
      default:
        console.log("Unknown route index:", index);
    }
  };

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <AnimatedDrawer
        drawerItems={drawerItems}
        onItemPress={handleItemPress}
        profileName="Book Reader"
        profileInitials="BR"
        drawerWidth={280}
      >
        <DrawerContent />
      </AnimatedDrawer>
    </GestureHandlerRootView>
  );
}
