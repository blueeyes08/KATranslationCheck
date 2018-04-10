import {NgModule} from '@angular/core';
import {MAT_DATE_LOCALE, MatAutocompleteModule, MatButtonModule, MatCardModule, MatChipsModule, MatDatepickerModule, MatDialogModule, MatExpansionModule, MatFormFieldModule, MatGridListModule, MatIconModule, MatInputModule, MatMenuModule, MatPaginatorModule, MatProgressSpinnerModule, MatSelectModule, MatSortModule, MatTableModule, MatToolbarModule, MatTooltipModule} from '@angular/material';
import {BrowserModule} from '@angular/platform-browser';

import {AppComponent} from './app.component';
import { AppRoutingModule } from './/app-routing.module';
import { TexttagEditorComponent } from './texttag-editor/texttag-editor.component';
import { PatternEditorComponent } from './pattern-editor/pattern-editor.component';
import { SingleTexttagEditorComponent } from './single-texttag-editor/single-texttag-editor.component';
import { SinglePatternEditorComponent } from './single-pattern-editor/single-pattern-editor.component';


@NgModule({
  declarations: [AppComponent, TexttagEditorComponent, PatternEditorComponent, SingleTexttagEditorComponent, SinglePatternEditorComponent],
  imports: [BrowserModule, MatToolbarModule, MatIconModule, AppRoutingModule],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule {
}
