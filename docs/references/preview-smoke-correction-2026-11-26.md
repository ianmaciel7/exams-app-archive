# Reviewed preview smoke correction

The previous browser smoke only asserted iframe src attributes, which could succeed while the HTTP server returned 404. Build the reviewed Loading and ErrorBoundary fixtures using the same pinned scripts as Pages; assert successful HTTP response, actual iframe content, visible loading spinner and retry interaction. Generated files stay in the CI checkout and are not committed. This does not certify any other historical preview.
