import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';
import { PatternEditorComponent } from './pattern-editor/pattern-editor.component';
import { TexttagEditorComponent } from './texttag-editor/texttag-editor.component';
import { ToolsComponent } from './tools/tools.component';

const routes: Routes = [
  {path: '', redirectTo: '/texttags', pathMatch: 'full'},
  {path: 'patterns', component: PatternEditorComponent},
  {path: 'texttags', component: TexttagEditorComponent},
  {path: 'tools', component: ToolsComponent},
];

@NgModule({imports: [RouterModule.forRoot(routes)], exports: [RouterModule]})
export class AppRoutingModule {
}
