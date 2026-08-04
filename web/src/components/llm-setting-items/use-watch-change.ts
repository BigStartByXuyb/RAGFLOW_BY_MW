import { settledModelVariableMap } from '@/constants/knowledge';
import { setChatVariableEnabledFieldValuePage } from '@/utils/chat';
import { useCallback } from 'react';
import { useFormContext } from 'react-hook-form';

export function useHandleFreedomChange(
  getFieldWithPrefix: (name: string) => string,
) {
  const form = useFormContext();

  const setLLMParameters = useCallback(
    (values: Record<string, any>, withPrefix: boolean) => {
      for (const key in values) {
        if (Object.prototype.hasOwnProperty.call(values, key)) {
          const realKey = getFieldWithPrefix(key);
          const element = values[key as keyof typeof values];

          form.setValue(withPrefix ? realKey : key, element);
        }
      }
    },
    [form, getFieldWithPrefix],
  );

  const handleChange = useCallback(
    (parameter: string) => {
      const currentValues = { ...form.getValues() };
      const values =
        settledModelVariableMap[
          parameter as keyof typeof settledModelVariableMap
        ];

      const nextValues = { ...currentValues, ...values };

      const variableCheckBoxFieldMap = setChatVariableEnabledFieldValuePage();

      setLLMParameters(values, true);
      setLLMParameters(variableCheckBoxFieldMap, false);
    },
    [form, setLLMParameters],
  );

  return handleChange;
}
