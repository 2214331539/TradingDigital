import { ChevronDown } from 'lucide-react'
import type { ModelInfo } from '../../../shared/types'

export function ModelSelector({
  models,
  selectedModel,
  onSelect,
}: {
  models: ModelInfo[]
  selectedModel: string | null
  onSelect: (id: string) => void
}) {
  const active = models.find((model) => model.id === selectedModel)

  return (
    <label className="model-selector">
      <span>{active?.name ?? '选择模型'}</span>
      <ChevronDown size={15} />
      <select value={selectedModel ?? ''} onChange={(event) => onSelect(event.target.value)}>
        {models.map((model) => (
          <option key={model.id} value={model.id}>
            {model.name}
          </option>
        ))}
      </select>
    </label>
  )
}

