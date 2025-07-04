import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { UserProvider } from "@/context/UserContext";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Quizzy Chess - Think Before You Take",
  description: "A multiplayer chess platform that integrates educational quizzes into gameplay",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{__html:`
          tailwind.config = {
            theme: {
              extend: {
                colors: {
                  gold: {
                    50: '#fffbea',
                    100: '#fef3c7',
                    200: '#fde68a',
                    300: '#fcd34d',
                    400: '#fbbf24',
                    500: '#f59e0b',
                    600: '#d97706',
                    700: '#b45309',
                    800: '#92400e',
                    900: '#78350f',
                  },
                  primary: '#fbbf24',
                  accent: '#b45309',
                },
              },
            },
          }
        `}} />
      </head>
      <body className={inter.className + " bg-gradient-to-br from-gold-50 to-white min-h-screen"}>
        <UserProvider>
          {children}
        </UserProvider>
      </body>
    </html>
  );
}
