import React, { useState, useCallback } from 'react';
import { Box } from 'ink';
import type { AppState } from '../state/AppState.js';
import { InteractiveScreen } from '../screens/InteractiveScreen.js';

interface AppProps {
  initialState: AppState;
}

export function App({ initialState }: AppProps): React.ReactElement {
  const [appState, setAppState] = useState<AppState>(initialState);

  const updateAppState = useCallback((fn: (prev: AppState) => AppState) => {
    setAppState(fn);
  }, []);

  return (
    <Box flexDirection="column" width="100%">
      <InteractiveScreen
        appState={appState}
        setAppState={updateAppState}
      />
    </Box>
  );
}
