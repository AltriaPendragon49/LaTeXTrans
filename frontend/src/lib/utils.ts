/**
 * 通用工具函数
 */
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * 合并 Tailwind CSS 类名，自动解决冲突
 * @param inputs - 任意数量的类名输入（字符串、对象、数组等）
 * @returns 合并并去重后的类名字符串
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
