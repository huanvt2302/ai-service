"use client"

import * as React from "react"
import { ThemeProvider as NextThemeProvider } from "next-themes"

export function ThemeProvider({ children, ...props }: any) {
  return <NextThemeProvider {...props}>{children}</NextThemeProvider>
}
