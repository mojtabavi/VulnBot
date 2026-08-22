import React from 'react';
import { Box, Text } from 'ink';

export default function StatusBar(props: {
  executor: string;
  model: string;
  hint?: string;
}): React.ReactElement {
  return (
    <Box>
      <Text backgroundColor="magenta" color="black"> {' octopus '} </Text>
      <Text color="gray"> executor </Text>
      <Text color="cyan">{props.executor}</Text>
      <Text color="gray">  ·  model </Text>
      <Text color="green">{props.model}</Text>
      {props.hint ? (
        <>
          <Text color="gray">  ·  </Text>
          <Text color="yellow">{props.hint}</Text>
        </>
      ) : null}
    </Box>
  );
}
