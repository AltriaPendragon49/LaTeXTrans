ALTER TABLE public.translation_tasks
ADD COLUMN IF NOT EXISTS detail_code TEXT;

ALTER TABLE public.translation_tasks
ADD COLUMN IF NOT EXISTS detail_params JSONB;
