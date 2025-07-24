"use client"

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import {
  useAppDispatch,
  LANGUAGE_OPTIONS,
  useAppSelector,
  GRAPH_OPTIONS,
  GRAPH_OPTIONS_GROUPED,
} from "@/common"
import type { Language } from "@/types"
import { setGraphName, setLanguage } from "@/store/reducers/global"

export function GraphSelect() {
  const dispatch = useAppDispatch()
  const graphName = useAppSelector((state) => state.global.graphName)
  const agentConnected = useAppSelector((state) => state.global.agentConnected)
  const onGraphNameChange = (val: string) => {
    dispatch(setGraphName(val))
  }

  return (
    <>
      <Select
        value={graphName}
        onValueChange={onGraphNameChange}
        disabled={agentConnected}
      >
        <SelectTrigger className="w-auto max-w-full">
          <SelectValue placeholder="Graph" />
        </SelectTrigger>
        <SelectContent className="max-h-[400px]">
          <Accordion type="multiple" defaultValue={Object.keys(GRAPH_OPTIONS_GROUPED)} className="w-full">
            {Object.entries(GRAPH_OPTIONS_GROUPED).map(([groupName, options]) => (
              <AccordionItem value={groupName} key={groupName} className="border-b-0">
                <AccordionTrigger className="py-2 hover:no-underline">
                  <span className="text-sm font-medium">{groupName}</span>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="flex flex-col gap-1 pl-2">
                    {options.map((item) => (
                      <SelectItem value={item.value} key={item.value} className="cursor-pointer">
                        {item.label}
                      </SelectItem>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </SelectContent>
      </Select>
    </>
  )
}

export function LanguageSelect() {
  const dispatch = useAppDispatch()
  const language = useAppSelector((state) => state.global.language)
  const agentConnected = useAppSelector((state) => state.global.agentConnected)

  const onLanguageChange = (val: Language) => {
    dispatch(setLanguage(val))
  }

  return (
    <>
      <Select
        value={language}
        onValueChange={onLanguageChange}
        disabled={agentConnected}
      >
        <SelectTrigger className="w-32">
          <SelectValue placeholder="Language" />
        </SelectTrigger>
        <SelectContent>
          {LANGUAGE_OPTIONS.map((item) => {
            return (
              <SelectItem value={item.value} key={item.value}>
                {item.label}
              </SelectItem>
            )
          })}
        </SelectContent>
      </Select>
    </>
  )
}
