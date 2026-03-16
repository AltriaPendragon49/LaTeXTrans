import { useState, useRef, useCallback, type ChangeEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from '@/store/useStore'
import { uploadFile } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Upload, X, File, CheckCircle2, AlertTriangle, Loader2, FileArchive } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'

type UploadErrorShape = {
    response?: {
        data?: {
            detail?: string
        }
    }
    message?: string
}

export const DropZone = () => {
    const { setTaskId, setLatexValidation, setArxivId, resetTranslationState } = useStore()
    const { t } = useTranslation()
    const [isDragActive, setIsDragActive] = useState(false)
    const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle')
    const [progress, setProgress] = useState(0)
    const [fileName, setFileName] = useState<string>('')
    const inputRef = useRef<HTMLInputElement>(null)

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setIsDragActive(true)
        } else if (e.type === 'dragleave') {
            setIsDragActive(false)
        }
    }, [])

    const processFile = useCallback(async (file: File) => {
        const validExtensions = ['.zip', '.rar', '.tar', '.gz', '.tgz', '.tex']
        const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()

        if (!validExtensions.includes(ext)) {
            toast.error(t('upload.unsupported_file_type_upload_a_zip_rar_tar_gz_or_tex_file'))
            return
        }

        if (file.size > 50 * 1024 * 1024) {
            toast.error(t('upload.file_size_exceeds_the_50_mb_limit'))
            return
        }

        // Reset previous task state only, preserve user configuration
        resetTranslationState()

        setFileName(file.name)
        setUploadStatus('uploading')
        setProgress(0)

        // Simulate progress since axios progress hook isn't exposed in api.ts yet
        const interval = setInterval(() => {
            setProgress(prev => {
                if (prev >= 90) return prev
                return prev + 10
            })
        }, 200)

        try {
            const response = await uploadFile(file as File)

            clearInterval(interval)
            setProgress(100)
            setUploadStatus('success')

            setTaskId(response.task_id)

            if (response.latex_validation) {
                setLatexValidation(response.latex_validation)
                if (response.latex_validation.is_valid) {
                    toast.success(t('upload.file_uploaded_successfully_and_passed_validation'))
                } else {
                    toast.warning(t('upload.file_uploaded_successfully_but_validation_found_issues'))
                }
            } else {
                toast.success(t('upload.file_uploaded_successfully'))
            }

            // Clear ArXiv ID to switch mode
            setArxivId(null)

        } catch (error: unknown) {
            clearInterval(interval)
            setUploadStatus('error')
            const uploadError = error as UploadErrorShape
            console.error('[DropZone] Upload failed', uploadError)
            toast.error(t('upload.upload_failed'))
        }
    }, [resetTranslationState, setArxivId, setLatexValidation, setTaskId, t])

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragActive(false)

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            processFile(e.dataTransfer.files[0])
        }
    }, [processFile])

    const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
        e.preventDefault()
        if (e.target.files && e.target.files[0]) {
            processFile(e.target.files[0])
        }
    }

    const resetUpload = (e: React.MouseEvent) => {
        e.stopPropagation()
        setUploadStatus('idle')
        setFileName('')
        setProgress(0)
        if (inputRef.current) inputRef.current.value = ''
        setLatexValidation(null)
    }

    const openFileDialog = () => {
        inputRef.current?.click()
    }

    const { latexValidation } = useStore() // Get latest validation state

    return (
        <div className="w-full space-y-4">
            <motion.div
                layout
                className={cn(
                    "relative overflow-hidden rounded-xl border-2 border-dashed transition-all duration-300 ease-in-out cursor-pointer group",
                    isDragActive
                        ? "border-primary bg-primary/5 shadow-lg scale-[1.01]"
                        : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30",
                    uploadStatus === 'error' && "border-destructive/50 bg-destructive/5",
                    uploadStatus === 'success' && "border-primary/50 bg-primary/5"
                )}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={openFileDialog}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <input
                    ref={inputRef}
                    type="file"
                    className="hidden"
                    accept=".zip,.rar,.tar,.tar.gz,.tgz,.tex"
                    onChange={handleChange}
                />

                <div className="flex flex-col items-center justify-center p-8 min-h-[200px] text-center space-y-4">
                    <AnimatePresence mode="wait">
                        {uploadStatus === 'idle' && (
                            <motion.div
                                key="idle"
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.9 }}
                                className="flex flex-col items-center space-y-2"
                            >
                                <div className="p-4 rounded-full bg-background shadow-sm border group-hover:scale-110 transition-transform duration-300">
                                    <Upload className="w-8 h-8 text-primary/80" />
                                </div>
                                <div className="space-y-1">
                                    <p className="text-lg font-medium">{t('upload.click_to_upload_or_drag_a_file_here')}</p>
                                    <p className="text-sm text-muted-foreground max-w-xs mx-auto">
                                        {t('upload.supports_zip_rar_tar_gz_archives_or_a_single_tex_file_max_50_mb')}
                                    </p>
                                </div>
                            </motion.div>
                        )}

                        {uploadStatus === 'uploading' && (
                            <motion.div
                                key="uploading"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="flex flex-col items-center space-y-4 w-full max-w-xs"
                            >
                                <div className="relative">
                                    <Loader2 className="w-10 h-10 text-primary animate-spin" />
                                    <div className="absolute inset-0 flex items-center justify-center">
                                        <span className="text-[10px] font-bold">{progress}%</span>
                                    </div>
                                </div>
                                <div className="text-sm font-medium">{fileName}</div>
                                <div className="h-1 w-full bg-muted rounded-full overflow-hidden">
                                    <motion.div
                                        className="h-full bg-primary"
                                        initial={{ width: 0 }}
                                        animate={{ width: `${progress}%` }}
                                    />
                                </div>
                                <p className="text-xs text-muted-foreground animate-pulse">{t('upload.uploading_and_validating')}</p>
                            </motion.div>
                        )}

                        {uploadStatus === 'success' && (
                            <motion.div
                                key="success"
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="flex flex-col items-center space-y-2 w-full"
                            >
                                <div className="p-3 rounded-full bg-primary/10 text-primary mb-2">
                                    <FileArchive className="w-8 h-8" />
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="font-medium text-lg">{fileName}</span>
                                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                                </div>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={resetUpload}
                                    className="text-muted-foreground hover:text-foreground mt-2"
                                >
                                    <X className="w-4 h-4 mr-2" />
                                    {t('upload.replace_file')}
                                </Button>
                            </motion.div>
                        )}

                        {uploadStatus === 'error' && (
                            <motion.div
                                key="error"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="flex flex-col items-center space-y-2"
                            >
                                <div className="p-3 rounded-full bg-destructive/10 text-destructive mb-2">
                                    <AlertTriangle className="w-8 h-8" />
                                </div>
                                <p className="font-medium text-destructive">{t('upload.upload_failed')}</p>
                                <Button variant="outline" size="sm" onClick={resetUpload}>
                                    {t('common.actions.retry')}
                                </Button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </motion.div>

            {/* Validation Results Card */}
            <AnimatePresence>
                {uploadStatus === 'success' && latexValidation && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className={cn(
                            "rounded-lg border p-4 text-sm",
                            latexValidation.is_valid ? "bg-card border-border" : "bg-destructive/5 border-destructive/20"
                        )}
                    >
                        <div className="flex items-start gap-3">
                            {latexValidation.is_valid ? (
                                <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5 shrink-0" />
                            ) : (
                                <AlertTriangle className="w-5 h-5 text-destructive mt-0.5 shrink-0" />
                            )}

                            <div className="space-y-2 w-full">
                                <h4 className={cn("font-medium", !latexValidation.is_valid && "text-destructive")}>
                                    {latexValidation.is_valid ? t('upload.valid_latex_project') : t('upload.invalid_latex_project')}
                                </h4>

                                {latexValidation.main_file && (
                                    <div className="flex items-center gap-2 text-muted-foreground">
                                        <File className="w-4 h-4" />
                                        <span>{t('upload.main_entry_file')}<span className="text-foreground font-mono">{latexValidation.main_file}</span></span>
                                    </div>
                                )}

                                {(latexValidation.warnings.length > 0 || latexValidation.errors.length > 0) && (
                                    <div className="space-y-1 pt-2 border-t border-border/50">
                                        {latexValidation.errors.map((err, i) => (
                                            <div key={`err-${i}`} className="flex items-center gap-2 text-destructive">
                                                <X className="w-3 h-3" />
                                                <span>{err}</span>
                                            </div>
                                        ))}
                                        {latexValidation.warnings.map((warn, i) => (
                                            <div key={`warn-${i}`} className="flex items-center gap-2 text-yellow-500">
                                                <AlertTriangle className="w-3 h-3" />
                                                <span>{warn}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}
