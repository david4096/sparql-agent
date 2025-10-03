import React from 'react';
import { Box, IconButton, Tooltip } from '@mui/material';
import { ContentCopy } from '@mui/icons-material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { QueryResults } from '@types/index';
import { copyToClipboard } from '@utils/export';
import toast from 'react-hot-toast';

interface JSONViewProps {
  results: QueryResults;
}

const JSONView: React.FC<JSONViewProps> = ({ results }) => {
  const jsonString = JSON.stringify(results, null, 2);

  const handleCopy = async () => {
    const success = await copyToClipboard(jsonString);
    if (success) {
      toast.success('Copied to clipboard');
    } else {
      toast.error('Failed to copy');
    }
  };

  return (
    <Box position="relative">
      <Tooltip title="Copy JSON">
        <IconButton
          onClick={handleCopy}
          sx={{
            position: 'absolute',
            right: 8,
            top: 8,
            zIndex: 1,
            bgcolor: 'background.paper',
          }}
        >
          <ContentCopy />
        </IconButton>
      </Tooltip>
      <SyntaxHighlighter
        language="json"
        style={tomorrow}
        customStyle={{
          margin: 0,
          borderRadius: 4,
          maxHeight: 600,
          overflow: 'auto',
        }}
      >
        {jsonString}
      </SyntaxHighlighter>
    </Box>
  );
};

export default JSONView;
