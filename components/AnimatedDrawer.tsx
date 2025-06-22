import React, { useMemo, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Dimensions,
  StyleSheet,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  interpolate,
  Extrapolate,
} from "react-native-reanimated";
import { SafeAreaView } from "react-native-safe-area-context";

const { width: SCREEN_WIDTH } = Dimensions.get("window");

type DrawerItem = {
  icon: string;
  title: string;
  subtitle: string;
};

type AnimatedDrawerProps = {
  drawerWidth?: number;
  children: React.ReactNode;
  drawerItems?: DrawerItem[];
  profileName?: string;
  profileInitials?: string;
  onItemPress?: (item: DrawerItem, index: number) => void;
  onLogout?: () => void;
  renderDrawerHeader?: () => React.ReactElement;
  renderDrawerFooter?: () => React.ReactElement;
  renderDrawerItem?: (
    item: DrawerItem,
    index: number,
    toggleDrawer: () => void
  ) => React.ReactElement;
  drawerStyle?: object;
  contentStyle?: object;
};

export const AnimatedDrawer: React.FC<AnimatedDrawerProps> = ({
  drawerWidth = SCREEN_WIDTH * 0.75,
  children,
  drawerItems = [],
  profileName = "John Doe",
  profileInitials = "JD",
  onItemPress,
  onLogout,
  renderDrawerHeader,
  renderDrawerFooter,
  renderDrawerItem,
  drawerStyle,
  contentStyle,
}) => {
  // 0 = closed, 1 = open
  const openProgress = useSharedValue(0);
  const DRAWER_WIDTH = drawerWidth;

  const toggleDrawer = useCallback(() => {
    openProgress.value = withTiming(openProgress.value === 0 ? 1 : 0, {
      duration: 350,
    });
  }, [openProgress]);

  // Optimized drawer animation with interpolation
  const animatedDrawerStyle = useAnimatedStyle(() => {
    const translateX = interpolate(
      openProgress.value,
      [0, 1],
      [-DRAWER_WIDTH, 0],
      Extrapolate.CLAMP
    );

    return {
      transform: [{ translateX }],
    };
  }, []);

  // Optimized content animation with smaller zoom effect
  const animatedContentStyle = useAnimatedStyle(() => {
    const scale = interpolate(
      openProgress.value,
      [0, 1],
      [1, 0.7], // Reduced zoom out effect
      Extrapolate.CLAMP
    );

    const translateX = interpolate(
      openProgress.value,
      [0, 1],
      [0, DRAWER_WIDTH * 0.6], // Smoother slide
      Extrapolate.CLAMP
    );

    const borderRadius = interpolate(
      openProgress.value,
      [0, 1],
      [0, 16],
      Extrapolate.CLAMP
    );

    return {
      transform: [{ scale }, { translateX }],
      borderRadius,
    };
  }, []);

  // Optimized overlay animation
  const overlayStyle = useAnimatedStyle(() => {
    const opacity = interpolate(
      openProgress.value,
      [0, 1],
      [0, 0.3],
      Extrapolate.CLAMP
    );

    return {
      opacity,
      pointerEvents: openProgress.value > 0 ? "auto" : "none",
    };
  }, []);

  // Default drawer items if none provided
  const defaultDrawerItems = useMemo(
    () => [
      { icon: "🏠", title: "Home", subtitle: "Main dashboard" },
      { icon: "👤", title: "Profile", subtitle: "Manage account" },
      { icon: "⚙️", title: "Settings", subtitle: "App preferences" },
      { icon: "📊", title: "Analytics", subtitle: "View reports" },
      { icon: "💬", title: "Messages", subtitle: "Chat & notifications" },
      { icon: "❓", title: "Help", subtitle: "Support & FAQ" },
      { icon: "🏠", title: "Home", subtitle: "Main dashboard" },
      { icon: "👤", title: "Profile", subtitle: "Manage account" },
      { icon: "⚙️", title: "Settings", subtitle: "App preferences" },
      { icon: "📊", title: "Analytics", subtitle: "View reports" },
      { icon: "💬", title: "Messages", subtitle: "Chat & notifications" },
      { icon: "❓", title: "Help", subtitle: "Support & FAQ" },
      { icon: "🏠", title: "Home", subtitle: "Main dashboard" },
    ],
    []
  );

  const itemsToRender =
    drawerItems.length > 0 ? drawerItems : defaultDrawerItems;

  const defaultRenderDrawerItem = useCallback(
    (item: any, index: number) => (
      <TouchableOpacity
        key={index}
        style={styles.drawerItem}
        onPress={() => {
          console.log("=== DRAWER ITEM TOUCHED ===");
          console.log("TouchableOpacity onPress triggered");
          console.log("Item:", item);
          console.log("Index:", index);
          console.log("onItemPress function exists:", !!onItemPress);

          if (onItemPress) {
            console.log("Calling onItemPress...");
            onItemPress(item, index);
            console.log("onItemPress called successfully");
          } else {
            console.log(`No onItemPress handler - Selected: ${item.title}`);
          }

          console.log("Calling toggleDrawer...");
          toggleDrawer();
          console.log("toggleDrawer called successfully");
        }}
        activeOpacity={0.7}
      >
        <View style={styles.drawerItemContent}>
          <View style={styles.drawerItemIcon}>
            <Text style={styles.drawerItemIconText}>{item.icon}</Text>
          </View>
          <View style={styles.drawerItemText}>
            <Text style={styles.drawerItemTitle}>{item.title}</Text>
          </View>
        </View>
      </TouchableOpacity>
    ),
    [toggleDrawer, onItemPress]
  );

  const defaultRenderDrawerHeader = useCallback(
    () => (
      <View style={styles.drawerHeader}>
        <View style={styles.drawerProfile}>
          <View style={styles.drawerAvatar}>
            <Text style={styles.drawerAvatarText}>{profileInitials}</Text>
          </View>
          <View style={styles.drawerProfileInfo}>
            <Text style={styles.drawerProfileName}>{profileName}</Text>
          </View>
        </View>
      </View>
    ),
    [profileName, profileInitials]
  );

  const defaultRenderDrawerFooter = useCallback(
    () => (
      <View style={styles.drawerFooter}>
        <TouchableOpacity
          style={styles.drawerLogout}
          onPress={() => {
            if (onLogout) {
              onLogout();
            }
            toggleDrawer();
          }}
        >
          <Text style={styles.drawerLogoutIcon}>🚪</Text>
          <Text style={styles.drawerLogoutText}>Logout</Text>
        </TouchableOpacity>
      </View>
    ),
    [toggleDrawer, onLogout]
  );

  return (
    <SafeAreaView style={{ flex: 1 }}>
      <View style={styles.container}>
        {/* Drawer */}
        <Animated.View
          style={[
            styles.drawerBase,
            { width: DRAWER_WIDTH - 100 },
            animatedDrawerStyle,
            drawerStyle,
          ]}
        >
          {renderDrawerHeader
            ? renderDrawerHeader()
            : defaultRenderDrawerHeader()}

          <View style={styles.drawerContent}>
            {itemsToRender.map((item, index) =>
              renderDrawerItem
                ? renderDrawerItem(item, index, toggleDrawer)
                : defaultRenderDrawerItem(item, index)
            )}
          </View>

          {renderDrawerFooter
            ? renderDrawerFooter()
            : defaultRenderDrawerFooter()}
        </Animated.View>

        {/* Overlay */}
        <Animated.View style={[styles.overlay, overlayStyle]}>
          <TouchableOpacity
            style={styles.overlayTouchable}
            onPress={toggleDrawer}
            activeOpacity={1}
          />
        </Animated.View>

        {/* Main Content */}
        <Animated.View
          style={[styles.contentBase, animatedContentStyle, contentStyle]}
        >
          {React.isValidElement(children)
            ? React.cloneElement(children as React.ReactElement<any>, {
                toggleDrawer,
              })
            : children}
        </Animated.View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    flexDirection: "row",
    backgroundColor: "black",
  },

  // Drawer Styles
  drawerBase: {
    position: "absolute",
    left: 0,
    top: 10,
    bottom: 50,
    backgroundColor: "#000",
    shadowColor: "#000",
    shadowOffset: { width: 2, height: 0 },
    shadowOpacity: 0.25,
    shadowRadius: 10,
    elevation: 10,
    zIndex: 2,
  },
  drawerHeader: {
    paddingTop: 60,
    paddingHorizontal: 20,
    paddingBottom: 18,
    borderBottomWidth: 1,
    borderBottomColor: "#333",
  },
  drawerProfile: {
    flexDirection: "row",
    alignItems: "center",
  },
  drawerAvatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: "#4a90e2",
    alignItems: "center",
    justifyContent: "center",
  },
  drawerAvatarText: {
    color: "#fff",
    fontSize: 12,
  },
  drawerProfileInfo: {
    marginLeft: 15,
    flex: 1,
  },
  drawerProfileName: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 2,
  },
  drawerContent: {
    flex: 1,
    paddingTop: 20,
  },
  drawerItem: {
    marginHorizontal: 15,
    marginVertical: 2,
    borderRadius: 12,
    overflow: "hidden",
  },
  drawerItemContent: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 5,
    paddingHorizontal: 5,
  },
  drawerItemIcon: {
    width: 20,
    height: 20,
    borderRadius: 20,
    backgroundColor: "#333",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 15,
  },
  drawerItemIconText: {
    fontSize: 12,
  },
  drawerItemText: {
    flex: 1,
  },
  drawerItemTitle: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "500",
    marginBottom: 2,
  },
  drawerFooter: {
    paddingHorizontal: 20,
    paddingVertical: 0,
    borderTopWidth: 1,
    borderTopColor: "#333",
  },
  drawerLogout: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
  },
  drawerLogoutIcon: {
    fontSize: 20,
    marginRight: 15,
  },
  drawerLogoutText: {
    color: "#ff6b6b",
    fontSize: 16,
    fontWeight: "500",
  },

  // Overlay
  overlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "#000",
    zIndex: 1,
  },
  overlayTouchable: {
    flex: 1,
  },

  // Content Styles
  contentBase: {
    flex: 1,
    backgroundColor: "#fff",
    overflow: "hidden",
  },
});
