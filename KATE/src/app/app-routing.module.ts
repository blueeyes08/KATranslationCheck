import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

const routes: Routes = [
  {path: '', redirectTo: '/recalls', pathMatch: 'full'},
  {path: 'recalls', component: FilterableRecallListComponent},
  {path: 'recall/:db/:dbid', component: RecallDetailsComponent},
  {path: 'analysis/:analysis', component: AnalysisOverviewComponent},
  {path: 'analysis', component: AnalysisOverviewComponent},
  {path: 'login', component: LoginComponent},
  {path: 'account', component: AccountViewComponent},
];

@NgModule({imports: [RouterModule.forRoot(routes)], exports: [RouterModule]})
export class AppRoutingModule {
}
