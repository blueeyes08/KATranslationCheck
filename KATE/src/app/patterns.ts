export interface FileCount {
    [file: string]: number;
}

export interface Pattern {
    english: string;
    translated: string;
    count: number;
    untranslated_count: number;
    translation_is_proofread: string;
    files: FileCount;
}