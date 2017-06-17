# Sendit

This is a dummy server for testing sending and receiving of data from an endpoint. The main job of the server will be to "sniff" for receiving a complete dicom series folder in a mapped data folder, and then to do the following:

   - Add query with images as objects to the database. 
   - A folder, the result of a query, is represented as a "Batch"
   - A single Dicom image is represented as an "Image"

Images will be moved around and processed on the level of a Batch, which is typically associated with a single accession number, series, and study, however there might be exceptions to this case. For module and modality specific docs and setup instructions, see our [documentation](https://pydicom.github.io/sendit/). If anything is missing documentation please [open an issue](https://www.github.com/pydicom/sendit)
